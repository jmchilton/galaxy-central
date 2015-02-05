#!/usr/bin/env python
"""
"""
import sys
import os
import pprint
import unittest

__GALAXY_ROOT__ = os.getcwd() + '/../../../'
sys.path.append( __GALAXY_ROOT__ + 'lib' )

from galaxy import eggs
eggs.require( 'SQLAlchemy >= 0.4' )
import sqlalchemy

from galaxy import model
from galaxy import exceptions
from galaxy.util.bunch import Bunch

import mock
from test_ModelManager import BaseTestCase
from galaxy.managers.datasets import DatasetManager
from galaxy.managers.datasets import DatasetAssociationManager
from galaxy.managers.histories import HistoryManager
from galaxy.managers.hdas import HDAManager


# =============================================================================
default_password = '123456'
user2_data = dict( email='user2@user2.user2', username='user2', password=default_password )
user3_data = dict( email='user3@user3.user3', username='user3', password=default_password )


# =============================================================================
class DatasetManagerTestCase( BaseTestCase ):

    def set_up_managers( self ):
        super( DatasetManagerTestCase, self ).set_up_managers()
        self.dataset_mgr = DatasetManager( self.app )

    def test_create( self ):
        self.log( "should be able to create a new Dataset" )
        dataset1 = self.dataset_mgr.create( self.trans )
        self.assertIsInstance( dataset1, model.Dataset )
        self.assertEqual( dataset1, self.trans.sa_session.query( model.Dataset ).get( dataset1.id ) )

    def test_base( self ):
        dataset1 = self.dataset_mgr.create( self.trans )
        dataset2 = self.dataset_mgr.create( self.trans )

        self.log( "should be able to query" )
        datasets = self.trans.sa_session.query( model.Dataset ).all()
        self.assertEqual( self.dataset_mgr.list( self.trans ), datasets )
        self.assertEqual( self.dataset_mgr.one( self.trans, filters=( model.Dataset.id == dataset1.id ) ), dataset1 )
        self.assertEqual( self.dataset_mgr.by_id( self.trans, dataset1.id ), dataset1 )
        self.assertEqual( self.dataset_mgr.by_ids( self.trans, [ dataset2.id, dataset1.id ] ), [ dataset2, dataset1 ] )

        self.log( "should be able to limit and offset" )
        self.assertEqual( self.dataset_mgr.list( self.trans, limit=1 ), datasets[0:1] )
        self.assertEqual( self.dataset_mgr.list( self.trans, offset=1 ), datasets[1:] )
        self.assertEqual( self.dataset_mgr.list( self.trans, limit=1, offset=1 ), datasets[1:2] )

        self.assertEqual( self.dataset_mgr.list( self.trans, limit=0 ), [] )
        self.assertEqual( self.dataset_mgr.list( self.trans, offset=3 ), [] )

        self.log( "should be able to order" )
        self.assertEqual( self.dataset_mgr.list( self.trans, order_by=sqlalchemy.desc( model.Dataset.create_time ) ),
            [ dataset2, dataset1 ] )

    def test_delete( self ):
        item1 = self.dataset_mgr.create( self.trans )

        self.log( "should be able to delete and undelete an hda" )
        self.assertFalse( item1.deleted )
        self.assertEqual( self.dataset_mgr.delete( self.trans, item1 ), item1 )
        self.assertTrue( item1.deleted )
        self.assertEqual( self.dataset_mgr.undelete( self.trans, item1 ), item1 )
        self.assertFalse( item1.deleted )

    def test_purge_allowed( self ):
        self.trans.app.config.allow_user_dataset_purge = True
        item1 = self.dataset_mgr.create( self.trans )

        self.log( "should purge an hda if config does allow" )
        self.assertFalse( item1.purged )
        self.assertEqual( self.dataset_mgr.purge( self.trans, item1 ), item1 )
        self.assertTrue( item1.purged )

    def test_purge_not_allowed( self ):
        self.trans.app.config.allow_user_dataset_purge = False
        item1 = self.dataset_mgr.create( self.trans )

        self.log( "should raise an error when purging an hda if config does not allow" )
        self.assertFalse( item1.purged )
        self.assertRaises( exceptions.ConfigDoesNotAllowException, self.dataset_mgr.purge, self.trans, item1 )
        self.assertFalse( item1.purged )

    ##TODO: I'm unclear as to how these work, so I'm kicking this down the road a bit....
    #def test_access_permission( self ):
    #    owner = self.user_mgr.create( self.trans, **user2_data )
    #    dataset = self.dataset_mgr.create( self.trans )
    #    # giving one user access permission makes it non-public, removing access for anyone else
    #    self.dataset_mgr.give_access_permission( self.trans, dataset, owner )
    #
    #    user3 = self.user_mgr.create( self.trans, **user3_data )
    #    user4 = self.user_mgr.create( self.trans,
    #        email='user4@user4.user4', username='user4', password=default_password )
    #
    #    self.assertTrue( self.dataset_mgr.has_access_permission( self.trans, dataset, owner ) )
    #    self.assertFalse( self.dataset_mgr.has_access_permission( self.trans, dataset, user3 ) )
    #    self.assertFalse( self.dataset_mgr.has_access_permission( self.trans, dataset, user4 ) )
    #
    #    # should be able to progressively add more roles without removing the previous
    #    self.dataset_mgr.give_access_permission( self.trans, dataset, user3 )
    #    self.assertTrue( self.dataset_mgr.has_access_permission( self.trans, dataset, user3 ) )
    #    self.assertTrue( self.dataset_mgr.has_access_permission( self.trans, dataset, owner ) )
    #    self.assertFalse( self.dataset_mgr.has_access_permission( self.trans, dataset, user4 ) )
    #
    #    #self.assertTrue( self.dataset_mgr.is_accessible( self.trans, dataset, owner ) )
    #    #self.assertFalse( self.dataset_mgr.is_accessible( self.trans, dataset, non_owner ) )

    def test_accessible( self ):
        owner = self.user_mgr.create( self.trans, **user2_data )
        non_owner = self.user_mgr.create( self.trans, **user3_data )

        dataset = self.dataset_mgr.create( self.trans )

        self.log( "(by default, dataset permissions are lax) should be accessible to all" )
        for user in self.user_mgr.list( self.trans ):
            self.assertTrue( self.dataset_mgr.is_accessible( self.trans, dataset, user ) )


# =============================================================================
class DatasetAssociationManagerTestCase( BaseTestCase ):

    def set_up_managers( self ):
        super( DatasetAssociationManagerTestCase, self ).set_up_managers()
        self.dataset_mgr = DatasetAssociationManager( self.app )
        self.hda_mgr = HDAManager( self.app )
        self.history_mgr = HistoryManager( self.app )

    #def test_metadata( self ):
    #    owner = self.user_mgr.create( self.trans, **user2_data )
    #    history1 = self.history_mgr.create( self.trans, name='history1', user=owner )
    #    dataset1 = self.dataset_mgr.create( self.trans )
    #
    #    self.log( "should be able to create a new HDA with a specified history and dataset" )
    #    hda1 = self.hda_mgr.create( self.trans, history=history1, dataset=dataset1, hid=1 )


# =============================================================================
if __name__ == '__main__':
    # or more generally, nosetests test_resourcemanagers.py -s -v
    unittest.main()
