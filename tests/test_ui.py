from flask import Flask, render_template

app = Flask(__name__, template_folder='.', static_folder='.', static_url_path='/static')

@app.route('/')
def index():
    return render_template('index.html', api_token="TEST_MODE")

@app.route('/api/neuro_status')
def neuro_status():
    import random
    from flask import jsonify
    return jsonify({
        "prefrontal": random.choice(["ACTIVE", "THINKING..."]),
        "motor": random.choice(["IDLE", "CALIBRATING"]),
        "sensory": "ONLINE",
        "language": random.choice(["LISTENING", "PROCESSING", "WAITING"]),
        "memory": random.choice(["SYNCED", "INDEXING"]),
        "dopamine": random.choice(["STABLE", "HIGH", "LOW"]),
        "cortisol": random.choice(["LOW", "STABLE", "HIGH"])
    })

if __name__ == "__main__":
    import os
    os.system("title JARVIS UI Test Mode")
    print("==================================================")
    print("  UI TEST MODE - JARVIS WEB DASHBOARD")
    print("  Running on http://127.0.0.1:8080")
    print("  (AI and Neural Cores are OFF)")
    print("==================================================")
    app.run(port=8080, debug=False)
