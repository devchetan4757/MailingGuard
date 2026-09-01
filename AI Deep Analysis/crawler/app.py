from flask import Flask, request, render_template_string
from crawler import crawl

app = Flask(__name__)


PAGE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Simple URL Crawler</title>

    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 30px;
            background: #f5f5f5;
        }

        h1 {
            color: #222;
        }

        form {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
        }

        input {
            flex: 1;
            padding: 12px;
            font-size: 16px;
            border: 1px solid #ccc;
            border-radius: 5px;
        }

        button {
            padding: 12px 25px;
            cursor: pointer;
            border: none;
            border-radius: 5px;
        }

        .result {
            background: white;
            padding: 20px;
            margin-top: 20px;
            border: 1px solid #ccc;
            border-radius: 5px;
        }

        .links {
            max-height: 400px;
            overflow-y: auto;
        }

        .link {
            padding: 10px;
            border-bottom: 1px solid #ddd;
            word-break: break-all;
        }

        .internal {
            color: green;
        }

        .external {
            color: blue;
        }

        .preview {
            margin-top: 20px;
            background: white;
            border: 1px solid #ccc;
            padding: 20px;
            border-radius: 5px;
        }

        .html-frame {
            width: 100%;
            height: 700px;
            border: 1px solid #ccc;
            background: white;
        }

        .error {
            color: red;
            font-weight: bold;
            background: #ffe5e5;
            padding: 10px;
            border-radius: 5px;
        }
    </style>
</head>

<body>

    <h1>Simple URL Crawler</h1>

    <form method="POST">

        <input
            type="text"
            name="url"
            placeholder="https://example.com"
            value="{{ url }}"
            required
        >

        <button type="submit">
            Analyze
        </button>

    </form>


    {% if error %}
        <p class="error">
            {{ error }}
        </p>
    {% endif %}


    {% if result %}

        <div class="result">

            <h2>Page Information</h2>

            <p>
                <strong>URL:</strong>
                {{ result["url"] }}
            </p>

            <p>
                <strong>Title:</strong>
                {{ result["title"] or "Not found" }}
            </p>

            <p>
                <strong>Meta Description:</strong>
                {{ result["meta_description"] or "Not found" }}
            </p>

            <p>
                <strong>Total Links:</strong>
                {{ result["link_count"] }}
            </p>

        </div>


        <div class="result">

            <h2>Links Found</h2>

            <div class="links">

                {% for link in result["links"] %}

                    <div class="link">

                        {% if link["internal"] %}

                            <strong class="internal">
                                [INTERNAL]
                            </strong>

                        {% else %}

                            <strong class="external">
                                [EXTERNAL]
                            </strong>

                        {% endif %}

                        <br><br>

                        <a
                            href="{{ link["url"] }}"
                            target="_blank"
                        >
                            {{ link["url"] }}
                        </a>

                        {% if link["text"] %}

                            <br>

                            <small>
                                {{ link["text"] }}
                            </small>

                        {% endif %}

                    </div>

                {% endfor %}

            </div>

        </div>


        <div class="preview">

            <h2>Fetched HTML Preview</h2>

            <iframe
                class="html-frame"
                sandbox
                srcdoc="{{ result['html'] | e }}">
            </iframe>

        </div>

    {% endif %}


</body>
</html>
"""


@app.route("/", methods=["GET", "POST"])
def home():

    url = ""
    result = None
    error = ""

    if request.method == "POST":

        url = request.form.get("url", "").strip()

        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        try:
            result = crawl(url)

        except Exception as e:
            error = str(e)

    return render_template_string(
        PAGE,
        url=url,
        result=result,
        error=error
    )


if __name__ == "__main__":

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )