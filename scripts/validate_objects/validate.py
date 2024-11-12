import sys
import os
from glob import glob
from pathlib import Path
import json
import logging
import datetime
from jsonschema import validate
from digitalhub.factory.factory import factory

# Paths to specs to validate and to schemas
spec_path = "/path/to/items/to/validate"
schema_path = "/path/to/schemas"

if len(sys.argv) >= 2:
    spec_path = sys.argv[1]

if len(sys.argv) >= 3:
    schema_path = sys.argv[2]

# Initialize logging
log_folder_name = "./logs"
os.makedirs(log_folder_name, exist_ok=True)

date = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
log_file_name = "validate_{0}.log".format(date)
log_path = "{0}/{1}".format(log_folder_name, log_file_name)

logging.basicConfig(filename=log_path,
        filemode='a',
        format='%(levelname)s - %(message)s',
        datefmt='%H:%M:%S',
        level=logging.DEBUG)

# Build dict: kind -> path to schema file
schemas = {}
for path_to_schema in glob(schema_path + '/**/*.json', recursive=True):
    kind = Path(path_to_schema).stem
    schemas[kind] = path_to_schema

# Build array: {spec file name, spec file full path}
specs = []
for path_to_spec in glob(spec_path + '/**/*.json', recursive=True):
    specs.append({
                "file_name": os.path.basename(path_to_spec),
                "path": path_to_spec
            })

# Validation
starting_message = "Commencing validation for {0} file(s).".format(len(specs))
logging.info(starting_message)
print(starting_message)

err_counter = 0
failures = []

for spec in specs:
    logging.debug(spec["file_name"])
    with open(spec["path"]) as spec_file:
        try:
            entity = json.load(spec_file)

            kind = entity["kind"]
            spec_json = entity["spec"]

            logging.debug("Building from spec...")

            built = factory.build_spec(kind, **spec_json)

            with open(schemas[kind]) as schema_file:
                schema = json.load(schema_file)

            logging.debug("Validating...")

            validate(instance=built.to_dict(), schema=schema)
            logging.info("OK: {0} was used to instantiate a valid object!".format(spec["file_name"]))

        except Exception as e:
            err_counter += 1
            failures.append({
                    "file_name": spec["file_name"],
                    "exception": e.__class__.__name__
                })
            logging.exception("{0} failed the validation process:".format(spec["file_name"]))
            continue

# Results
logging.info("Validation completed.")

if not err_counter:
    success_message = "All generated objects are valid!"
    logging.info(success_message)
    print(success_message)
else:
    failure_message = "Process failed for {0} file(s):".format(err_counter)
    logging.info(failure_message)
    for failure in failures:
        logging.info("{0} - {1}".format(failure["file_name"], failure["exception"]))

    print(failure_message + " view logs in {0} for more information.".format(log_file_name))
