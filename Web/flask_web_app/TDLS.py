from flask import Flask, jsonify, request

app = Flask(__name__)

# 임시 데이터베이스 (리스트)
todos = []

# 1. Create (할 일 추가) - POST 방식
@app.route('/todos', methods=['POST'])
def create_todo():
    request_data = request.get_json() # 보낸 데이터 받기
    new_todo = {
        'id': len(todos) + 1,
        'task': request_data['task']
    }
    todos.append(new_todo)
    return jsonify(new_todo), 201

# 2. Read (전체 목록 조회) - GET 방식
@app.route('/todos', methods=['GET'])
def get_todos():
    return jsonify({'todos': todos})

# 3. Update (할 일 수정) - PUT 방식
@app.route('/todos/<int:todo_id>', methods=['PUT'])
def update_todo(todo_id):
    request_data = request.get_json()
    for todo in todos:
        if todo['id'] == todo_id:
            todo['task'] = request_data['task']
            return jsonify(todo)
    return jsonify({'error': 'Not found'}), 404

# 4. Delete (할 일 삭제) - DELETE 방식
@app.route('/todos/<int:todo_id>', methods=['DELETE'])
def delete_todo(todo_id):
    global todos
    todos = [t for t in todos if t['id'] != todo_id] # 해당 ID 제외하고 재구성
    return jsonify({'message': 'Deleted successfully'}), 204

if __name__ == '__main__':
    app.run(debug=True)