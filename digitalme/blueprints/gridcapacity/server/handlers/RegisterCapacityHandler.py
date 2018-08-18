# THIS FILE IS SAFE TO EDIT. It will not be overwritten when rerunning go-raml.

import json as JSON
import os
from datetime import datetime

import jsonschema
from jsonschema import Draft4Validator

from flask import jsonify, request
from jumpscale import j

from digitalme.blueprints.gridcapacity.models import Capacity, NodeRegistration, NodeNotFoundError, Farmer, FarmerRegistration
from .jwt import validate_farmer_id, FarmerInvalid

dir_path = os.path.dirname(os.path.realpath(__file__))
Capacity_schema = JSON.load(open(dir_path + '/schema/Capacity_schema.json'))
Capacity_schema_resolver = jsonschema.RefResolver('file://' + dir_path + '/schema/', Capacity_schema)
Capacity_schema_validator = Draft4Validator(Capacity_schema, resolver=Capacity_schema_resolver)


def RegisterCapacityHandler():
    inputs = request.get_json()
    try:
        iyo_organization = validate_farmer_id(inputs.pop('farmer_id'))
    except FarmerInvalid:
        return jsonify(errors='Unauthorized farmer'), 403

    try:
        Capacity_schema_validator.validate(inputs)
    except jsonschema.ValidationError as e:
        return jsonify(errors="bad request body: {}".format(e)), 400

    # Update the node if already exists or create new one using the inputs
    farmers = FarmerRegistration.list(organization=iyo_organization)
    if not farmers:
        return jsonify(errors='Unauthorized farmer'), 403

    farmer = farmers[0]
    inputs['updated'] = datetime.now()

    try:
        capacity = NodeRegistration.get(inputs.get("node_id"))
        if farmer.location:
            capacity.location = farmer.location

        inputs['farmer'] = farmer
        capacity = capacity.ddict_hr
        capacity.update(**inputs)
    except NodeNotFoundError:
        inputs['farmer'] = iyo_organization
        capacity = Capacity.schema.get(data=inputs)
        if farmer.location:
            capacity.location = farmer.location
        Capacity.set(capacity)
        capacity = capacity.ddict_hr

    return capacity, 201, {'Content-type': 'application/json'}
