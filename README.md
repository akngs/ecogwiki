# Install

1.   Create new Google App Engine application
2.   Create ``app.yaml`` by copying ``app.yaml.sample``
3.   [Optional] Create ``schema-custom.json`` by copying ``schema-custom.json.sample`` if you want to define custom schema
4.   Change application id appropriately
5.   Deploy and wait for index building (takes a few minutes)
6.   Edit ``.config`` page. See [this example](http://www.ecogwiki.com/.config?_type=txt)
7.   Done


# How to run tests

Execute following command on project home:

    python run_tests.py <APP_ENGINE_SDK_PATH> <TEST_PACKAGE_PATH>

Example:

    python run_tests.py /usr/local/Cellar/google-app-engine/1.8.1/share/google-app-engine ./tests


# How to use

See [Ecogwiki Help page](http://www.ecogwiki.com/Help)
