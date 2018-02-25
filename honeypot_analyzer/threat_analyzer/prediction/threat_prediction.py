"""Launches predictions to Google API Prediction."""

import os

from googleapiclient import discovery, errors
from oauth2client.client import GoogleCredentials
from oauth2client.client import ApplicationDefaultCredentialsError

from absl import app
from absl import flags
from absl import logging

from honeypot_server.conf import settings

PROJECT_ID = 'honeypotprediction'
MODEL_ID = 'toll_fraud'
MODEL_TYPE = 'CLASSIFICATION'

BUCKET = 'honeypot_invite/INVITE_20180218_20180223_TRAINING.csv'
PREDICTIONS_FILE = 'predictions.csv'



FLAGS = flags.FLAGS


def get_service():
    """Get Service from Google Cloud API"""
    try:
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = '%s' % settings.CREDENTIALS
        credentials = GoogleCredentials.get_application_default()
    except ApplicationDefaultCredentialsError as e:
        logging.exception(e)
    return discovery.build('prediction', 'v1.6', credentials=credentials)


def insert_model():
    api = get_service()
    logging.info('Inserting Model into Google Prediction API')
    api.trainedmodels().insert(project=PROJECT_ID, body={
        'id': MODEL_ID,
        'storageDataLocation': BUCKET,
        'modelType': MODEL_TYPE
    }).execute()


def check_model():
    api = get_service()
    analysis = api.trainedmodels().analyze(project=PROJECT_ID, id=MODEL_ID).execute()
    logging.info(analysis)


def get_model_training_status():
    api = get_service()
    model_status = api.trainedmodels().get(project=PROJECT_ID, id=MODEL_ID).execute()
    training_status = model_status.get('trainingStatus')
    if training_status:
        logging.info('Model training status: %s' % training_status)


def read_predictions():
    with open(PREDICTIONS_FILE) as f:
        return f.readline()


def predict(individual_prediction):
    """

    :param individual_prediction: (list) List of values.
    :return:
    """
    logging.info('Perform predictions for %r' % individual_prediction)
    api = get_service()
    prediction = api.trainedmodels().predict(project=PROJECT_ID, id=MODEL_ID, body={
        'input': {
            'csvInstance': individual_prediction
        },
    }).execute()
    label = prediction.get('outputLabel')
    stats = prediction.get('outputMulti')
    logging.info('Label: %s Stats: %s' % (label, stats))
    return int(label), stats


def main(_):

    # get_model_training_status()
    # check_model()
    individual_prediction = read_predictions().split(',')
    predict(individual_prediction)


if __name__ == '__main__':
    app.run(main)
