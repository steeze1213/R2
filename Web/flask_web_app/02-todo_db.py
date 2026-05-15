from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

app.config['SQLALCHEMY_DATABASE_URI'] = (
    'mysql+pymysql://root:0000@localhost:3306/example'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)


class Todo(db.Model):
    __tablename__ = 'todos'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    task = db.Column(db.Text, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'task': self.task
        }


@app.route('/todos', methods=['POST'])
def create_todo():
    data = request.get_json()

    if not data or 'task' not in data:
        return jsonify({'error': 'task is required'}), 400

    todo = Todo(task=data['task'])
    db.session.add(todo)
    db.session.commit()

    return jsonify(todo.to_dict()), 201


@app.route('/todos', methods=['GET'])
def get_todos():
    todos = Todo.query.all()
    return jsonify({
        'todos': [todo.to_dict() for todo in todos]
    })


@app.route('/todos/<int:todo_id>', methods=['PUT'])
def update_todo(todo_id):
    data = request.get_json()

    if not data or 'task' not in data:
        return jsonify({'error': 'task is required'}), 400

    todo = Todo.query.get(todo_id)
    if not todo:
        return jsonify({'error': 'Not found'}), 404

    todo.task = data['task']
    db.session.commit()

    return jsonify(todo.to_dict())


@app.route('/todos/<int:todo_id>', methods=['DELETE'])
def delete_todo(todo_id):
    todo = Todo.query.get(todo_id)
    if not todo:
        return jsonify({'error': 'Not found'}), 404

    db.session.delete(todo)
    db.session.commit()

    return jsonify({'message': 'Deleted successfully'}), 204


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)