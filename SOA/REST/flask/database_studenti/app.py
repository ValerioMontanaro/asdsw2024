import flask
from flask import request, jsonify

app = flask.Flask(__name__)

students = [
    {
    'id': 0,
    'nome': 'Marco',
    'cognome': 'Rossi',
    'immatricolazione': 2018,
    'esami_sostenuti': 12
    },
    {
    'id': 1,
    'nome': 'Maria',
    'cognome': 'Bianchi',
    'immatricolazione': 2019,
    'esami_sostenuti': 13
    }
]

# Se non metto nulla in GET
@app.route('/', methods=['GET'])
def home():
    return '''<h1>Database Studenti</h1>
    <p>Per accedere all'enenco studenti indicare il percorso /api/v1/resources/students/all'''

# la lista dei metodi accettati contiene solamente GET
@app.route('/api/v1/resources/students/all', methods=['GET'])
def api_all():
    return jsonify(students)

# Permette di accedere ad un singolo studente tramite il suo id sia in GET che in POST
@app.route('/api/v1/resources/students', methods=['GET', 'POST', 'DELETE'])
def app_id():

    # se il metodo è GET
    if request.method == 'GET':
        # vedi se c'è un id nella richiesta
        if 'id' in request.args:
            id_ = int(request.args['id'])
        else:
            return '''<h2>ERROR: indicare un id</h2>'''

        results = []

        # scorri la lista degli studenti e se trovi l'id richiesto lo aggiungi alla lista dei risultati
        for student in students:
            if student['id'] == id_:
                results.append(student)

        return jsonify(results)
    
    # se il metodo è POST
    elif request.method == 'POST':
        student = {}
       
        student['id'] = int(request.args['id'])
        student['nome'] = request.args['nome']
        student['cognome'] = request.args['cognome']
        student['immatricolazione'] = int(request.args['immatricolazione'])
        student['esami_sostenuti'] = int(request.args['esami_sostenuti'])

        students.append(student)

        return jsonify(student)
    
    else:
        
        if 'id' in request.args:
            id_ = int(request.args['id'])
        else:
            return '''<h2>ERROR: indicare un id</h2>'''

        for student in students:
            if student['id'] == id_:
                to_delete = student

        students.remove(to_delete)

        return jsonify(students)

app.run()
