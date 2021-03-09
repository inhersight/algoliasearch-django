import six

from django.conf import settings
from mock import patch
from django.test import TestCase

from algoliasearch_django import algolia_engine
from algoliasearch_django import AlgoliaIndex
from algoliasearch_django import AlgoliaEngine
from algoliasearch_django.registration import AlgoliaEngineError
from algoliasearch_django.registration import RegistrationError
from django.db.models import signals

from .models import Website, User


class EngineTestCase(TestCase):
    def setUp(self):
        self.engine = AlgoliaEngine()

    def tearDown(self):
        for elt in self.engine.get_registered_models():
            self.engine.unregister(elt)

    def test_init_exception(self):
        algolia_settings = dict(settings.ALGOLIA)
        del algolia_settings['APPLICATION_ID']
        del algolia_settings['API_KEY']

        with self.settings(ALGOLIA=algolia_settings):
            with self.assertRaises(AlgoliaEngineError):
                AlgoliaEngine(settings=settings.ALGOLIA)

    def test_auto_discover_indexes(self):
        """Test that the `index` module was auto-discovered and the models registered"""

        six.assertCountEqual(
            self,
            [
                User,  # Registered using the `register` decorator
                Website,  # Registered using the `register` method
            ],
            algolia_engine.get_registered_models()
        )

    def test_is_register(self):
        self.engine.register(Website)
        self.assertTrue(self.engine.is_registered(Website))
        self.assertFalse(self.engine.is_registered(User))

    def test_get_adapter(self):
        self.engine.register(Website)
        self.assertEquals(AlgoliaIndex,
                          self.engine.get_adapter(Website).__class__)

    def test_get_adapter_exception(self):
        with self.assertRaises(RegistrationError):
            self.engine.get_adapter(Website)

    def test_get_adapter_from_instance(self):
        self.engine.register(Website)
        instance = Website()
        self.assertEquals(
            AlgoliaIndex,
            self.engine.get_adapter_from_instance(instance).__class__)

    def test_register(self):
        self.engine.register(Website)
        self.engine.register(User)
        self.assertIn(Website, self.engine.get_registered_models())
        self.assertIn(User, self.engine.get_registered_models())

    def test_register_exception(self):
        self.engine.register(Website)
        self.engine.register(User)

        with self.assertRaises(RegistrationError):
            self.engine.register(Website)

    def test_register_with_custom_index(self):
        class WebsiteIndex(AlgoliaIndex):
            pass

        self.engine.register(Website, WebsiteIndex)
        self.assertEqual(WebsiteIndex.__name__,
                         self.engine.get_adapter(Website).__class__.__name__)

    @patch.object(signals.post_save, 'connect')
    @patch.object(signals.pre_delete, 'connect')
    def test_register_with_implicit_autoindexing(self, mock_pre_delete_connect, mock_post_save_connect):
        class WebsiteIndex(AlgoliaIndex):
            pass

        engine = AlgoliaEngine()
        engine.register(Website, WebsiteIndex)

        self.assertTrue(mock_post_save_connect.called)
        self.assertTrue(mock_pre_delete_connect.called)

    @patch.object(signals.post_save, 'connect')
    @patch.object(signals.pre_delete, 'connect')
    def test_register_with_autoindexing(self, mock_pre_delete_connect, mock_post_save_connect):
        class WebsiteIndex(AlgoliaIndex):
            pass

        engine = AlgoliaEngine()
        engine.register(Website, WebsiteIndex, auto_indexing=True)

        self.assertTrue(mock_post_save_connect.called)
        self.assertTrue(mock_pre_delete_connect.called)

    @patch.object(signals.post_save, 'connect')
    @patch.object(signals.pre_delete, 'connect')
    def test_register_without_autoindexing(self, mock_pre_delete_connect, mock_post_save_connect):
        class WebsiteIndex(AlgoliaIndex):
            pass

        engine = AlgoliaEngine()
        engine.register(Website, WebsiteIndex, auto_indexing=False)

        self.assertFalse(mock_post_save_connect.called)
        self.assertFalse(mock_pre_delete_connect.called)

    def test_register_with_custom_index_exception(self):
        class WebsiteIndex(object):
            pass

        # WebsiteIndex is not a subclass of AlgoliaIndex
        with self.assertRaises(RegistrationError):
            self.engine.register(Website, WebsiteIndex)

    def test_unregister(self):
        self.engine.register(Website)
        self.engine.register(User)
        self.engine.unregister(Website)

        registered_models = self.engine.get_registered_models()
        self.assertNotIn(Website, registered_models)
        self.assertIn(User, registered_models)

    def test_unregister_exception(self):
        self.engine.register(User)

        with self.assertRaises(RegistrationError):
            self.engine.unregister(Website)
