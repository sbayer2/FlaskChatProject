from flask import Flask, request, jsonify, render_template_string
import openai
import time
import os

app = Flask(__name__)

# Replace with your actual OpenAI API key
openai.api_key = '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'
client = openai.OpenAI(api_key=openai.api_key)
ASSISTANT = None
threads = {}

def submit_message(assistant_id, thread, user_message):
    client.beta.threads.messages.create(
        thread_id=thread.id, role="user", content=user_message
    )
    return client.beta.threads.runs.create(
        thread_id=thread.id,
        assistant_id=assistant_id,
    )

def get_response(thread):
    return client.beta.threads.messages.list(thread_id=thread.id, order="asc")

def create_thread_and_run(user_input):
    thread = client.beta.threads.create()
    run = submit_message(ASSISTANT, thread, user_input)
    return thread, run

def wait_on_run(run, thread):
    while run.status in ["queued", "in_progress"]:
        run = client.beta.threads.runs.retrieve(
            thread_id=thread.id,
            run_id=run.id,
        )
        time.sleep(0.5)
    return run

@app.route('/create_assistant', methods=['POST'])
def create_assistant():
    global ASSISTANT

    # Define the parameters for the new assistant
    assistant_params = {
        "instructions": "You are a helpful assistant chatbot",
        "name": "chatbot",
        "tools": [{"type": "code_interpreter"}],
        "model": "gpt-4-turbo"
    }

    # Create the new assistant
    response = client.beta.assistants.create(**assistant_params)
    ASSISTANT = response.id

    return jsonify({"message": "Assistant created", "assistant_id": ASSISTANT})

FORM_HTML = '''
<!DOCTYPE html>
<html>
<head>
    <title>Chatbot</title>
</head>
<body>
    <h1>Chat with OpenAI Assistant</h1>
    <button id="create-assistant">Create Assistant</button>
    <form id="chat-form" method="POST" style="display:none;">
        <input type="hidden" id="thread_id" name="thread_id">
        <input type="text" id="message" name="user_input" placeholder="Type your message here">
        <button type="submit">Send</button>
    </form>
    <div id="response">{{ output|safe }}</div>
</body>
<script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
<script>
    $(function() {
        $('#create-assistant').on('click', function() {
            $.post('/create_assistant', function(data) {
                if (data.assistant_id) {
                    $('#create-assistant').hide();
                    $('#chat-form').show();
                    alert('Assistant created with ID: ' + data.assistant_id);
                } else if (data.error) {
                    alert('Error creating assistant: ' + data.error);
                }
            });
        });

        $('#chat-form').on('submit', function(event) {
            event.preventDefault();
            var message = $('#message').val();
            var threadId = $('#thread_id').val();
            $.post('/', { user_input: message, thread_id: threadId }, function(data) {
                if (data.response) {
                    $('#response').html(data.response);
                    $('#thread_id').val(data.thread_id);  // Store the thread ID for subsequent messages
                } else if (data.error) {
                    $('#response').html('Error: ' + data.error);
                }
            });
        });
    });
</script>
</html>
'''

@app.route('/', methods=['GET', 'POST'])
def home():
    global threads

    if request.method == 'POST':
        user_input = request.form['user_input']

        if 'thread_id' not in request.form or request.form['thread_id'] == '':
            thread1, run1 = create_thread_and_run(user_input)
            threads[thread1.id] = thread1
            run1 = wait_on_run(run1, thread1)
        else:
            thread_id = request.form['thread_id']
            thread1 = threads[thread_id]
            run1 = submit_message(ASSISTANT, thread1, user_input)
            run1 = wait_on_run(run1, thread1)

        messages = get_response(thread1)
        formatted_response = "<br>".join([f"{m.role.title()}: {m.content[0].text.value.replace('\n', '<br>')}" for m in messages.data])
        return jsonify({'response': formatted_response, 'thread_id': thread1.id})

    return render_template_string(FORM_HTML, output='')

@app.route('/readiness_check')
def readiness_check():
    if not os.environ.get("OPENAI_API_KEY"):
        return 'API key not set', 500
    return 'OK', 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)







