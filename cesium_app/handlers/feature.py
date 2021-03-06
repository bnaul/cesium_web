import tornado.ioloop

from cesium import featurize, time_series
from cesium.features import dask_feature_graph

from baselayer.app.handlers.base import BaseHandler
from baselayer.app.custom_exceptions import AccessError
from baselayer.app.access import auth_or_token
from ..models import DBSession, Dataset, Featureset, Project

from os.path import join as pjoin
import uuid
import datetime


class FeatureHandler(BaseHandler):
    @auth_or_token
    def get(self, featureset_id=None):
        if featureset_id is not None:
            featureset_info = Featureset.get_if_owned_by(featureset_id,
                                                         self.current_user)
        else:
            featureset_info = [f for p in self.current_user.projects
                               for f in p.featuresets]

        self.success(featureset_info)

    @auth_or_token
    async def _await_featurization(self, future, fset):
        """Note: we cannot use self.error / self.success here.  There is
        no longer an active, open request by the time this happens!
        That said, we can push notifications through to the frontend
        using flow.
        """
        try:
            result = await future

            fset = DBSession().merge(fset)
            fset.task_id = None
            fset.finished = datetime.datetime.now()
            DBSession().commit()

            self.action('baselayer/SHOW_NOTIFICATION',
                        payload={"note": "Calculation of featureset '{}' completed.".format(fset.name)})

        except Exception as e:
            DBSession().delete(fset)
            DBSession().commit()
            self.action('baselayer/SHOW_NOTIFICATION',
                        payload={"note": 'Cannot featurize {}: {}'.format(fset.name, e),
                                 "type": 'error'})
            print('Error featurizing:', type(e), e)

        self.action('cesium/FETCH_FEATURESETS')

    @auth_or_token
    async def post(self):
        data = self.get_json()
        featureset_name = data.get('featuresetName', '')
        dataset_id = int(data['datasetID'])
        features_to_use = [feature for (feature, selected) in data.items()
                           if feature in dask_feature_graph and selected]
        if not features_to_use:
            return self.error("At least one feature must be selected.")

        custom_feats_code = data['customFeatsCode'].strip()
        custom_script_path = None

        dataset = Dataset.query.filter(Dataset.id == dataset_id).one()
        if not dataset.is_owned_by(self.current_user):
            raise AccessError('No such data set')

        fset_path = pjoin(self.cfg['paths:features_folder'],
                          '{}_featureset.npz'.format(uuid.uuid4()))

        fset = Featureset(name=featureset_name,
                          file_uri=fset_path,
                          project=dataset.project,
                          features_list=features_to_use,
                          custom_features_script=None)
        DBSession().add(fset)

        client = await self._get_client()

        all_time_series = client.map(time_series.load,
                                     [f.uri for f in dataset.files])
        all_labels = client.map(lambda ts: ts.label, all_time_series)
        all_features = client.map(featurize.featurize_single_ts,
                                  all_time_series,
                                  features_to_use=features_to_use,
                                  custom_script_path=custom_script_path,
                                  raise_exceptions=False)
        computed_fset = client.submit(featurize.assemble_featureset,
                                      all_features, all_time_series)
        imputed_fset = client.submit(featurize.impute_featureset,
                                     computed_fset, inplace=False)
        future = client.submit(featurize.save_featureset, imputed_fset,
                               fset_path, labels=all_labels)
        fset.task_id = future.key
        DBSession().commit()

        loop = tornado.ioloop.IOLoop.current()
        loop.spawn_callback(self._await_featurization, future, fset)

        self.success(fset, 'cesium/FETCH_FEATURESETS')

    @auth_or_token
    def delete(self, featureset_id):
        f = Featureset.get_if_owned_by(featureset_id, self.current_user)
        DBSession().delete(f)
        DBSession().commit()
        self.success(action='cesium/FETCH_FEATURESETS')

    @auth_or_token
    def put(self, featureset_id):
        f = Featureset.get_if_owned_by(featureset_id, self.current_user)
        self.error("Functionality for this endpoint is not yet implemented.")
