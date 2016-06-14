
## Plays API

Index:
- [Running the tests](#running-the-tests)
- [Design choices](#design-choices)
- [Move to production](#move-to-production)
- [Installation](#installation)


### Running the Tests
For the sake of convenience, an Amazon EC2 instance has been set up to serve
the API. You can easily run the tests with the following command:
```
python test.py -H api.rxuriguera.com -P 80
```

**Important:** The original `test.py` was slightly modified in order to send a JSON body
for the POST requests. This is done to comply with the specification shown in the
description PDF. Please use the test script included in the project.

```python
# req = urllib2.Request(url, urllib.urlencode(data))
req = urllib2.Request(url, json.dumps(data), {'Content-Type': 'application/json'})
```

There is an additional API endpoint not present in the specification that
reinitializes the database: `POST /truncate_tables`.
The body of the request must contain a security flag set to true:

```json
{"truncate": true}
```

A [Jmeter](#) JMX test plan is included with the source code. It can be used to
easily test the performance of the API. Below are some request times in milliseconds.
Network latencies are included (server in central	Europe).

| Endpoint        | Concurrent Users | Total Calls |  Mean | Median | 90% Line | 95% Line |
|-----------------|--------:|------:|------:|-------:|---------:|---------:|
| add_channel     | 50      | 50000 |    94 |     89 |      121 |      134 |
| add_performer   | 50      | 50000 |    92 |     88 |      126 |      221 |
| add_song        | 50      | 50000 |   105 |    104 |      133 |      143 |
| add_play        | 50      | 50000 |   181 |    187 |      243 |      263 |

Querying a dataset of 10 channels, 30 songs and 1M plays spanning from 2015-01
to 2016-12 yielded the following results:
| Endpoint          | Concurrent Users | Total Calls |  Mean | Median | 90% Line | 95% Line |
|-------------------|--------:|------:|------:|-------:|---------:|---------:|
| get_channel_plays | 10      | 10000 |    91 |     88 |      109 |      121 |
| get_song_plays    | 10      | 10000 |    88 |     85 |      115 |      125 |
| get_top           | 10      | 10000 |   765 |    743 |     1250 |     1454 |

Request times for the `get_channel_plays` and `get_song_plays` are strongly
dependent on the start-end parameters. The broader the time range, the longer
the response body which results in higher network latencies. High `get_top`
time is due to the complexity of the query.


### Design Choices
[Flask](#http://flask.pocoo.org/) framework is used because
it is lightweight and no admin site or forms are needed for this pilot.
Unlike other specialized frameworks such as Django REST Frmaework, Flask comes
with no serializers. [Marshmallow](#https://marshmallow.readthedocs.io/en/latest/) is used for
validation and object serialization/deserialization.

As for the database, both a relational and NoSQL database were considered:
MySQL and **Cassandra**.

Though not a technical argument, the main reason why I chose
Cassandra over MySQL is that I had never used Cassandra before. It would
have been probably faster to implement this prototype using MySQL, but since I am applying
for a position where trying new technologies and algorithms is expected,
I took this as an opportunity to get started with a new tool.

There are other valid points to back up this decision:
- Cassandra
	- Pros:
		- **Fast writes**: Writes will be far more common than reads in our application (many channels steadily publishing plays).
		- Distributed and Fault tolerant: nodes can fail without
		  compromising uptime. P2P communication between nodes.
		- Scalability: reportedly, linear scalability
		- [Good for time series](#http://www.datastax.com/dev/blog/advanced-time-series-with-cassandra): rows can have millions of columns
	- Cons:
	 	- Complex Data Modelling: schema has to be carefully thought-out. Almost one table per query type.
- MySQL
	- Pros:
		- Complex and flexible queries
		- Widely used
		- All developers are familiar with SQL
	- Cons:
		- Does not scale as well as other alternatives
		- Master-Slave replication

Cassandra Query Language (CQL) is great but can be too limiting for situations
like the `get_top` feature.
After reading about algorithms for *top-k* queries, I have implemented one of the ones described in this
paper: [Best Position Algorithms for Top-k Queries](http://www-sop.inria.fr/members/Patrick.Valduriez/pmwiki/Patrick/uploads/Publications/AkbariniaBpaVLDB07.pdf).


### Move to Production
Some of the things that should be taken into account before moving the pilot to
a production environment:

- Validation: some basic validation of the input is already performed, but more
	checks should be done.
- It is probably a bad idea to use artists and songs name as identifiers.
- Pagination for the `get_song_plays` and  `get_channel_plays` endpoints
- Testing: Unit tests, integration tests, performance tests
- Add time information to the plays tables' partition key. Right now a single
  partition (song/channel) can grow to much, making it more difficult to
	distribute data evenly across the cluster.
- Logging and Monitoring
- Replication: add more nodes to the Cassandra cluster an set replication strategy.


### Notes on Scalability
There are two easy ways of scaling the application:
- Add more application servers behind a load balancer
- Add more nodes to the Cassandra cluster

Assuming that each channel inserts a new play every three minutes (average song time),
we get:
```
2000 channels * (24h * 60m / 3m) ~ 1M plays/day

1M plays / (24h * 60m * 60s) ~ 12 calls/second
```

Data ingestion should not be a problem with our current setup. Querying for plays
by channel or song, should also scale well.

The most compromising operation is the `get_top` endpoint. These are some things
that can be done to improve the performance of this method:
- Use a better `top-k` query algorithm
- Estimate the play counts: The exact number of plays is probably not that important (bound on the error). E.g. lossy counting
- Store aggregate counts per day and channel.
- It looks like the `get_top` call is something that a webpage could use to show
*weekly* top charts, by making calls with the same set of parameters. If
we always have the same few combinations of channels, it could be pretty
useful to cache or persist the top songs per week and group of channels.


### Installation
###### Virtual environment
```sh
mkdir plays-api
cd plays-api

pip install virtualenv
virtualenv venv

source activate venv/bin/activate

pip install -r requirements.txt
```

###### Cassandra
In order to install Cassandra you can follow this step by step guide:
[How to install Cassandra on Ubuntu 14.04](https://www.digitalocean.com/community/tutorials/how-to-install-cassandra-and-run-a-single-node-cluster-on-ubuntu-14-04)
Once installed, you must enable the following option in `cassandra.yml`
```yml
# UDFs (user defined functions) are disabled by default.
enable_user_defined_functions: true
```

Restart Cassandra service and log into using the cqlsh command
```
(venv) plays-api$ cqlsh
Connected to Plays API Cluster at 127.0.0.1:9042.
[cqlsh 5.0.1 | Cassandra 3.0.6 | CQL spec 3.4.0 | Native protocol v4]
Use HELP for help.
cqlsh>
```
Paste the contents of the file `db.cql` into the console. This will create the
`plays` keyspace and the needed user-defined functions.

Create the database tables by running the following command:
```sh
python manage.py sync
```

You can set the environment with the `APP_CONFIG` environment variable. Default
is `production`. Choose `development` to enable debugging.
```sh
export APP_CONFIG=development
```

Run a development server
```sh
python manage.py runserver
```
