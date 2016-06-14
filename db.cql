CREATE KEYSPACE plays
WITH REPLICATION = { 'class' : 'SimpleStrategy', 'replication_factor' : 1 };

USE plays;

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

-- Create a final function that is called after the state function has been 
-- called on every row
CREATE OR REPLACE AGGREGATE group_and_count(text, text) 
    SFUNC state_group_and_count 
    STYPE map<text, int> 
    INITCOND {};