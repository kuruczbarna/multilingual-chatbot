#
#
# main() will be run when you invoke this action
#
# @param Cloud Functions actions accept a single parameter, which must be a JSON object.
#
# @return The output of this action, which must be a JSON object.
#
#
import json
from watson_developer_cloud import AssistantV1, LanguageTranslatorV3

# consts
BASE_LANGUAGE = 'en'
LT_THRESH = 0.4
LT_PAIRS = {
    'ar': 'Arabic',
    'zh': 'Chinese (Simplified)',
    'zht': 'Chinese (Traditional)',
    'cz': 'Czech',
    'da': 'Danish',
    'nl': 'Dutch',
    'en': 'English',
    'fi': 'Finnish',
    'fr': 'French',
    'de': 'German',
    'hi': 'Hindi',
    'hu': 'Hungarian',
    'it': 'Italian',
    'ja': 'Japanese',
    'ko': 'Korean',
    'nb': 'Norwegian Bokmal',
    'pl': 'Polish',
    'pt': 'Portuguese (Brazil)',
    'ru': 'Russian',
    'es': 'Spanish',
    'sv': 'Swedish',
    'tr': 'Turkish'
}


def main( params ):
    # get conversation workspace id
    try:
        workspace = params['assistant_workspace_id']
    except:
        return {
            'message': 'Please bind your assistant workspace ID as parameter',
            'context': '{}',
            'output': '{}',
            'intents': '{}',
            'language': ''
        }

    # set up conversation
    try:
        assistant = AssistantV1(
            iam_apikey=params['assistant_apikey'],
            version='2019-03-06'
        )
    except:
        return {
            'message': 'Please bind your assistant service',
            'context': '{}',
            'output': '{}',
            'intents': '{}',
            'language': ''
        }

    # set up translator
    try:
        translator = LanguageTranslatorV3(
            version='2019-04-03',
            iam_apikey=params['translator_apikey']
        )
    except:
        return {
            'message': 'Please bind your language translator service',
            'context': '{}',
            'output': '{}',
            'intents': '{}',
            'language': ''
        }

    # check for empty or null string
    try:
        text = params['input']['text']
        print('User input: ' + text)
    except:
        text = ''

    # get conversation context if available
    try:
        context = json.loads( params['context'] )
    except:
        context = {}

    # detect language
    if text:
        response = translator.identify( text )
        res = response.get_result()
    else:
        res = None
    if res and res['languages'][0]['confidence'] > LT_THRESH:
        language = res['languages'][0]['language']
    elif res is None:
        language = BASE_LANGUAGE
    else:
        return {
            'message': 'Sorry, I am not able to detect the language you are speaking. Please try rephrasing.',
            'context': json.dumps( context ),
            'output': '{}',
            'intents': '{}',
            'language': ''
        }

    print('Detected user language: ' + language)

    # validate support for language
    if language not in LT_PAIRS.keys():
        return {
            'message': 'Sorry, I do not know how to translate between {} and {} yet.'.format(
                BASE_LANGUAGE, language
            ),
            'context': json.dumps( context ),
            'output': '{}',
            'intents': '{}',
            'language': language
        }

    # translate to base language if needed
    if language != BASE_LANGUAGE:
        response = translator.translate(
            text,
            source=language,
            target=BASE_LANGUAGE
        )
        res = response.get_result()
        text = res['translations'][0]['translation']

    # supply language as entity
    text += ' (@lng:{})'.format( language )
    print('Text in base language to be sent to Watson Assistant: ' + text)

    # hit conversation
    response = assistant.message(
        workspace_id=workspace,
        input={'text': text},
        context=context
    )
    res = response.get_result()
    print('Response from Watson Assistant: ')
    print(res)
    new_context = res['context']
    output = res['output']
    output_text = [text for text in res['output']['text'] if text]
    message = output_text[0]
    output['text'] = output_text
    intents = res['intents']

    # translate back to original language if needed
    if language != BASE_LANGUAGE:
        chatbotResponseIdentify = translator.identify( output )
        chatbotResponseLanguage = chatbotResponseIdentify.get_result()

        # translate only if chatbot response was NOT in target language
        if chatbotResponseLanguage and chatbotResponseLanguage['languages'][0]['confidence'] > LT_THRESH and chatbotResponseLanguage['languages'][0]['language'] != language:
            print('Response from Watson Assistant needs translation to target language...')
            response = translator.translate(
                output_text,
                source=BASE_LANGUAGE,
                target=language
            )
            res = response.get_result()
            output_text = [t['translation'] for t in res['translations']]
            message = output_text[0]
            output['text'] = output_text
            print('Watson response translated to target lang: ' + message)

    return {
        'message': message,
        'context': json.dumps( new_context ),
        'output': output,
        'intents': json.dumps( intents ),
        'language': language
    }
