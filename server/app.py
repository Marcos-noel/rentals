#!usr/bin/env python3

from datetime import date, timedelta, datetime
from re import M
from flask import Flask, jsonify, request, make_response, abort
from flask_migrate import Migrate
from flask_bcrypt import Bcrypt
from flask_jwt_extended import create_access_token, JWTManager, jwt_required, get_jwt_identity, decode_token, get_jwt
from flask_restful import Api, Resource
from flask_cors import CORS
from flask_bcrypt import check_password_hash
from werkzeug.security import generate_password_hash
from models import db, Customer, Property, Agent, Land, TokenBlocklist

# configuration
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///real.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = b'#\xab@\xcc\xa0\xb3E\xc3\xf4\x1a\\<&?\x91\xdb'
app.json.compact = False

# migrating app to db
migrate = Migrate(app, db)
CORS(app)

# JWT Configuration
app.config['JWT_SECRET_KEY'] = b'\xae\xc765\xe5\x99\x03a\xdd\x92\t\x92\x9f\x1f\xe5\xb1'
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=1) # Adjust token expiration as needed
jwt = JWTManager(app)

# initializing app
db.init_app(app)

bcrypt = Bcrypt(app)

api = Api(app)


# customer/visitor signup

class CustomerSignup(Resource):

    def post(self):

        data = request.get_json()

        hashed_password = bcrypt.generate_password_hash(data['password'])

        new_customer = Customer(
            email = data['email'],
            password = hashed_password
        )

        customer = Customer.query.filter(Customer.email == new_customer.email).first()

        if customer is not None:
            response = make_response(
                jsonify({
                    "error": "This account exists!"
                }),
                409
            )

            return response

        db.session.add(new_customer)
        db.session.commit()

        access_token = create_access_token(identity=new_customer.id)

        return make_response(jsonify({'message': 'Customer signup successful'}), 201, {'Authorization': f'Bearer {access_token}'})

api.add_resource(CustomerSignup, "/auth/signup") 


# customer/visitor login

class CustomerLogin(Resource):

    def post(self):

        data = request.get_json()

        email = data['email']
        password = data['password']

        customer = Customer.query.filter_by(email=email).first()

        if customer and bcrypt.check_password_hash(customer.password, password):

            access_token = create_access_token(identity=customer.id)

            return make_response(jsonify({'message': 'Customer login successful'}), 200, {'Authorization': f'Bearer {access_token}'})

        abort(401, 'Invalid username or password')

api.add_resource(CustomerLogin, '/auth/login')


# function to enable signout
@jwt.token_in_blocklist_loader
def check_if_token_in_blacklist(jwt_header, jwt_payload):
    jti = jwt_payload['jti']
    token = TokenBlocklist.query.filter_by(jti=jti).first()
    return token is not None

# customer/visitor signout

class CustomerSignout(Resource):

    @jwt_required()
    def post(self):
        jti = get_jwt()["jti"]
        now = datetime.utcnow()
        db.session.add(TokenBlocklist(jti=jti, created_at=now))
        db.session.commit()
        return make_response(jsonify({'message': 'Customer signout successful'}), 200)

api.add_resource(CustomerSignout, '/auth/signout')


# agent signup

class AgentSignup(Resource):

    def post(self):

        data = request.get_json()

        hashed_password = bcrypt.generate_password_hash(data['password'])

        new_agent = Agent(
            first_name = data['first_name'],
            last_name = data['last_name'],
            password = hashed_password,
            phone = data['phone'],
            email = data['email'],
            description = data['description'],
            reviews = data['reviews'],
            zipcode = data['zipcode'],
            no_of_properties = data['no_of_properties']
        )

        agent = Agent.query.filter(Agent.email == new_agent.email).first()

        if agent is not None:
            response = make_response(
                jsonify({
                    "error": "This account exists!"
                }),
                409
            )

            return response

        db.session.add(new_agent)
        db.session.commit()

        access_token = create_access_token(identity=new_agent.id)

        return make_response(jsonify({'message': 'Agent signup successful'}), 201, {'Authorization': f'Bearer {access_token}'})

api.add_resource(AgentSignup, "/agent/signup")


# agent login

class AgentLogin(Resource):

    def post(self):

        data = request.get_json()

        email = data['email']
        password = data['password']

        agent = Agent.query.filter_by(email=email).first()

        if agent and bcrypt.check_password_hash(agent.password, password):

            access_token = create_access_token(identity=agent.id)

            return make_response(jsonify({'message': 'Agent login successful'}), 200, {'Authorization': f'Bearer {access_token}'})

        abort(401, 'Invalid username or password')

api.add_resource(AgentLogin, '/agent/login')


# gets/fetches an agent's properties

class GetAgentProperties(Resource):

    @jwt_required()
    def get(self):
        current_user_id = get_jwt_identity()
        agent = Agent.query.get(current_user_id)
        if not agent:
            return make_response(jsonify({'error': 'Unauthorized access'}), 403)

        # Retrieve all properties associated with the agent
        agent_properties = Property.query.filter_by(agent_id=current_user_id).all()

        properties = [property.to_dict() for property in agent_properties]

        return make_response(jsonify(properties), 200)

api.add_resource(GetAgentProperties, '/agent/properties')


# gets/fetches an agent's lands

class GetAgentLands(Resource):

    @jwt_required()
    def get(self):

        current_user_id = get_jwt_identity()
        agent = Agent.query.get(current_user_id)
        if not agent:
            return make_response(jsonify({'error': 'Unauthorized access'}), 403)

        #Retrieve all lands associated with the agent
        agent_lands = Land.query.filter_by(agent_id=current_user_id).all()

        lands = [land.to_dict() for land in agent_lands]

        return make_response(jsonify(lands), 200)

api.add_resource(GetAgentLands, '/agent/lands')


# an agent to be able to add a new property or land in the system

class AgentNewPropertyOrLand(Resource):

    @jwt_required()
    def post(self):

        current_user_id = get_jwt_identity()
        agent = Agent.query.get(current_user_id)
        if not agent:
            return make_response(jsonify({'error': 'Unauthorized access'}), 403)

        data = request.get_json()

        resource_type = data.get('resource_type')
        if resource_type not in ['property', 'land']:
            abort(400, 'Invalid resource type')

        location = data.get('location')
        price = data.get('price')
        sale_type = data.get('sale_type')
        description = data.get('description')
        image = data.get('image')
        property_category = data.get('property_category')
        status = data.get('status')

        if resource_type == 'property':
            bedroom = data.get('bedroom')
            bathroom = data.get('bathroom')

            new_resource = Property(
                location=location,
                bedroom=bedroom,
                bathroom=bathroom,
                price=price,
                sale_type=sale_type,
                description=description,
                image=image,
                property_category=property_category,
                status=status,
                agent_id=current_user_id
            )

        elif resource_type == 'land':
            size = data.get('size')

            new_resource = Land(
                location=location,
                size=size,
                price=price,
                sale_type=sale_type,
                description=description,
                image=image,
                property_category=property_category,
                status=status,
                agent_id=current_user_id
            )

        db.session.add(new_resource)
        agent.no_of_properties += 1  # Increment the agent's no_of_properties
        db.session.commit()

        return make_response(jsonify(new_resource.to_dict()), 201)

api.add_resource(AgentNewPropertyOrLand, '/resources/add')


# an agent to be able to update his/her property data or land data

class AgentUpdatePropertyOrLand(Resource):

    @jwt_required()
    def patch(self):

        current_user_id = get_jwt_identity()
        agent = Agent.query.get(current_user_id)
        if not agent:
            return make_response(jsonify({'error': 'Unauthorized access'}), 403)

        data = request.get_json()

        resource_type = data.get('resource_type')
        resource_id = data.get('resource_id')
        if not resource_type or not resource_id:
            abort(400, 'resource_type and resource_id are required in the request')

        if resource_type == 'property':
            resource = Property.query.filter_by(id=resource_id, agent_id=current_user_id).first()
        elif resource_type == 'land':
            resource = Land.query.filter_by(id=resource_id, agent_id=current_user_id).first()
        else:
            abort(400, 'Invalid resource type')

        if not resource:
            abort(404, f'{resource_type.capitalize()} with id {resource_id} not found')

        for attr in data:
            if hasattr(resource, attr) and attr != 'id':
                setattr(resource, attr, data[attr])

        db.session.commit()

        response_dict = resource.to_dict()

        return make_response(jsonify(response_dict), 200)

api.add_resource(AgentUpdatePropertyOrLand, '/resources/update')


# an agent to be able to delete a property or land he/she owns

class AgentDeletePropertyOrLand(Resource):

    @jwt_required()
    def delete(self):

        current_user_id = get_jwt_identity()
        agent = Agent.query.get(current_user_id)
        if not agent:
            return make_response(jsonify({'error': 'Unauthorized access'}), 403)

        data = request.get_json()

        resource_type = data.get('resource_type')
        resource_id = data.get('resource_id')
        if not resource_type or not resource_id:
            abort(400, 'resource_type and resource_id are required in the request')

        if resource_type == 'property':
            resource = Property.query.filter_by(id=resource_id, agent_id=current_user_id).first()
        elif resource_type == 'land':
            resource = Land.query.filter_by(id=resource_id, agent_id=current_user_id).first()
        else:
            abort(400, 'Invalid resource type')

        if not resource:
            abort(404, f'{resource_type.capitalize()} with id {resource_id} not found')

        db.session.delete(resource)
        db.session.commit()

        response_dict = {"message": f"{resource_type.capitalize()} successfully deleted"}

        return make_response(jsonify(response_dict), 200)

api.add_resource(AgentDeletePropertyOrLand, '/resources/delete')


# an agent to be able to view his/her data(profile)

class GetAgentData(Resource):

    @jwt_required()
    def get(self):
        current_user_id = get_jwt_identity()
        agent = Agent.query.get(current_user_id)
        if not agent:
            return make_response(jsonify({'error': 'Unauthorized access'}), 403)

        agent_data = agent.to_dict()

        return make_response(jsonify(agent_data), 200)

api.add_resource(GetAgentData, '/agent-data')


# an agent is able to update his/her data(profile)

class UpdateAgentData(Resource):

    @jwt_required()
    def patch(self):
        current_user_id = get_jwt_identity()
        agent = Agent.query.get(current_user_id)
        if not agent:
            return make_response(jsonify({'error': 'Unauthorized access'}), 403)

        data = request.get_json()

        if not data:
            return make_response(jsonify({'error': 'No data provided'}), 400)

        for attr, value in data.items():
            if attr == 'password':
                # Hash the password before setting it
                value = bcrypt.generate_password_hash(value)
            if hasattr(agent, attr):
                setattr(agent, attr, value)

        db.session.commit()

        response_dict = agent.to_dict()

        return make_response(jsonify(response_dict), 200)

api.add_resource(UpdateAgentData, '/agent-data/update') 


# gets/fetches all properties and lands - to be viewed by everyone

class GetPropertiesAndLands(Resource):

    def get(self, resource_type):
        if resource_type == 'properties':
            resource_instances = Property.query.all()
        elif resource_type == 'lands':
            resource_instances = Land.query.all()
        else:
            abort(404, 'Invalid resource type')

        if not resource_instances:
            abort(404, f'No {resource_type.capitalize()} found')

        resource_data = [resource_instance.to_dict() for resource_instance in resource_instances]

        return make_response(jsonify(resource_data), 200)

api.add_resource(GetPropertiesAndLands, '/<string:resource_type>')        


# gets all agents in the system - to be viewed by admin

class GetAgents(Resource):

    def get(self):

        all_agents = Agent.query.all()
        if not all_agents:
            abort(404, 'No agents found')

        agents = []

        for agent_instance in all_agents:
            agent_data = agent_instance.to_dict()

            agents.append(agent_data)

        return make_response(jsonify(agents), 200)

api.add_resource(GetAgents, '/agents')      


if __name__ == '__main__':
    app.run(port=5555, debug=True)