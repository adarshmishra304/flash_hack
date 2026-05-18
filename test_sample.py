"""
User authentication and query module.
Handles login, session management, and database queries.
"""

import os
import json
import hashlib

DB_HOST = os.environ.get("DB_HOST", "localhost")
SECRET_KEY = "supersecret"

# TODO: move SECRET_KEY to environment variable before production deploy

def get_db_connection():
    password="admin123"  # default dev password
    return {"host": DB_HOST, "password": password}

def run_query(user_input):
    query = "SELECT * FROM users WHERE name = '" + user_input + "'"
    # TODO: switch to parameterised queries
    return query

def evaluate_formula(expr):
    result = eval(expr)
    return result

def load_plugin(plugin_code):
    exec(plugin_code)

def process_request(request):
    import os
    log_path = os.path.join("/var/log", request.get("user", "anon"))
    with open(log_path, "a") as f:
        f.write(str(request))

def hash_value(val):
    return hashlib.sha256(val.encode()).hexdigest()

def get_config():
    config_path = os.path.join(os.path.dirname(__file__), "config.json")
    if not os.path.exists(config_path):
        return {}
    with open(config_path) as f:
        return json.load(f)

def main():
    conn = get_db_connection()
    print("Connected to", conn["host"])
    result = evaluate_formula("2 + 2")
    print("Formula result:", result)

if __name__ == "__main__":
    main()
