import pytest
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support.ui import Select
import uuid
import os
import time
from os.path import join as pjoin
from util import test_project, test_dataset, test_featureset

test_featureset_name = str(uuid.uuid4())


def test_add_new_featureset(driver):
    driver.get('http://localhost:5000')
    driver.set_window_size(1920,1080)
    with test_project() as p:
        with test_dataset(p) as ds:
            driver.refresh()
            proj_select = Select(driver.find_element_by_css_selector('[name=project]'))
            proj_select.select_by_value(str(p.id))

            driver.find_element_by_id('react-tabs-4').click()
            driver.find_element_by_partial_link_text('Compute New Features').click()

            featureset_name = driver.find_element_by_css_selector('[name=featuresetName]')
            featureset_name.send_keys(test_featureset_name)

            # THE FOLLOWING DOES NOT WORK WITH PHANTOM JS
            # Test check/uncheck all features in group
            # amplitude = driver.find_element_by_css_selector('[name=sci_amplitude]')
            # assert amplitude.get_attribute('value') == 'true'
            # driver.save_screenshot("/tmp/checked.png")
            # driver.find_element_by_partial_link_text('Check/Uncheck All').click()
            # time.sleep(0.3)
            # driver.save_screenshot("/tmp/unchecked.png")
            # assert amplitude.get_attribute('value') == 'false'
            # driver.find_element_by_partial_link_text('Check/Uncheck All').click()
            # time.sleep(0.1)
            # assert amplitude.get_attribute('value') == 'true'

            # driver.find_element_by_id('react-tabs-14').click()
            # n_epochs = driver.find_element_by_css_selector('[name=obs_n_epochs]')
            # assert n_epochs.get_attribute('value') == 'true'
            # driver.find_element_by_partial_link_text('Check/Uncheck All').click()
            # time.sleep(0.1)
            # assert n_epochs.get_attribute('value') == 'false'

            # driver.find_element_by_id('react-tabs-16').click()
            # driver.find_element_by_partial_link_text('Check/Uncheck All').click()
            # assert driver.find_element_by_css_selector('[name=lmb_fold2P_slope_10percentile]')\
            #              .get_attribute('value') == 'false'


            driver.find_element_by_class_name('btn-primary').click()

            driver.implicitly_wait(1)
            status_td = driver.find_element_by_xpath(
                "//div[contains(text(),'Feature computation begun')]")
            status_td = driver.find_element_by_xpath("//td[contains(text(),'In progress')]")

            driver.implicitly_wait(10)
            status_td = driver.find_element_by_xpath("//td[contains(text(),'Completed')]")


def test_delete_featureset(driver):
    driver.get('http://localhost:5000')
    driver.set_window_size(1920,1080)
    with test_project() as p:
        with test_dataset(p) as ds:
            with test_featureset(p) as fs:
                driver.refresh()
                proj_select = Select(driver.find_element_by_css_selector('[name=project]'))
                proj_select.select_by_value(str(p.id))

                driver.find_element_by_id('react-tabs-4').click()
                driver.find_element_by_partial_link_text('Delete').click()
                driver.implicitly_wait(1)
                status_td = driver.find_element_by_xpath(
                    "//div[contains(text(),'Feature set successfully deleted')]")
                try:
                    el = driver.find_element_by_xpath(
                        "//td[contains(text(),'{}')]".format(test_featureset_name))
                except NoSuchElementException:
                    pass
                else:
                    raise Exception("Featureset still present in table after delete.")