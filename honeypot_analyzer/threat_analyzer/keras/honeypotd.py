import numpy as np

from flask import Flask, jsonify, request

from keras.models import model_from_json

# initialize our Flask application and the Keras model
app = Flask(__name__)
model = None

MODEL_NAME = 'honeypot.json'
MODEL_WEIGHTS = 'honeypot.h5'


def load_model():
    """
        load the pre-trained Keras model (here we are using a model
        pre-trained on ImageNet and provided by Keras, but you can
        substitute in your own networks just as easily)
    :return:
    """
    global model
    json_file = open(MODEL_NAME, 'r')
    loaded_model_json = json_file.read()
    json_file.close()
    model = model_from_json(loaded_model_json)
    # Load weights into new model.
    model.load_weights(MODEL_WEIGHTS)
    print('Loaded model from disk')


def prepare_data(data):
    """Build numpy array from Prediction."""
    prediction = np.array([data])
    print prediction.shape
    return prediction


@app.route('/predict', methods=['POST'])
def predict():
    # Initialize the data dictionary that will be returned from the view.
    data = {"success": False}

    values = request.get_json()
    required = ['caller']
    if not all(k in values for k in required):
        return 'Missing values', 400

    prediction_data = prepare_data(values['caller'])
    preds = model.predict(prediction_data)
    result = np.around(preds[:, 1]).astype('int32')
    response = {'results': 'Is a threat: %d Probability: %d' % result}
    # return the data dictionary as a JSON response
    return jsonify(response), 200


if __name__ == "__main__":
    print(("* Loading Keras model and Flask starting server..."
           "please wait until server has fully started..."))
    load_model()
    app.run()
