# Validate objects

This script is used to test that the creation of objects (entities, runtimes) works correctly. It takes the exported json files of a number of objects and uses their *spec* fields to generate instances through a factory method. Then, each generated instance is converted back to dict and validated against its kind's schema.

Usage:

```bash
    python3 validate.py "path/to/specs/to/validate" "path/to/schemas"
```

Within the script are two default paths. If you update these, you can omit the parameters:

```bash
    python3 validate.py
```