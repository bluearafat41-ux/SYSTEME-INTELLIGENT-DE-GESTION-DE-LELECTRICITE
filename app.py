from flask import Flask
app = Flask(__name__)
@app.route("/")
def home():
    return "systeme intelligent de gestion de l électricité - ca marche"
if __name__ == "__main__":
    app.run(debug=True)
    