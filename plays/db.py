# -*- coding: utf-8 -*-
import logging

from flask import Blueprint

from cassandra.cluster import Cluster
from cassandra.cqlengine import connection
from cassandra.cqlengine.management import create_keyspace_simple

logger = logging.getLogger()

db = Blueprint('db', __name__)
db.config = {}

cluster = None
session = None


@db.record
def record_params(setup_state):
    app = setup_state.app
    db.config = dict([(key,value) for (key,value) in app.config.iteritems()])
  
  
def init_db_blueprint():
    global cluster
    cluster = Cluster(
        db.config['CASSANDRA_CONTACT_POINTS']
    )
    
    global session
    session = cluster.connect(
        db.config['CASSANDRA_KEYSPACE']
    )
    
    connection.setup(
        db.config['CASSANDRA_CONTACT_POINTS'],
        db.config['CASSANDRA_KEYSPACE'], 
        protocol_version=3
    )
    
    initialize_keyspace()
    
    
def initialize_keyspace():
    logger.info("Initializing keyspace")
    create_keyspace_simple('plays', 1)
    
    # TODO: Activate automatic creation of udf an uda
    logger.info("Creating user-defined functions")
    udf = """
    -- Create a function that takes in state (any Cassandra type) as the first 
    -- parameter and any number of additional parameters
    CREATE OR REPLACE FUNCTION state_group_and_count( state map<text, int>, type_1 text, type_2 text)
        CALLED ON NULL INPUT
        RETURNS map<text, int>
        LANGUAGE java 
        AS '
            // Clean
            type_1 = type_1.replaceAll("\"", "\\\"");
            type_2 = type_2.replaceAll("\"", "\\\"");
        
            // Json list
            String key = "[\"" + type_1 + "\", \"" + type_2 + "\"]";
            
            Integer count = (Integer) state.get(key);
            
            if (count == null) count = 1; 
            else count++; 
            
            state.put(key, count); 
            
            return state; 
        ' ;
    """
    #session.execute(udf)
    
    logger.info("Creating user-defined aggregations")
    uda = """
    -- Create a final function that is called after the state function has been 
    -- called on every row
    CREATE OR REPLACE AGGREGATE group_and_count(text, text) 
        SFUNC state_group_and_count 
        STYPE map<text, int> 
        INITCOND {};
    """
    #session.execute(uda)