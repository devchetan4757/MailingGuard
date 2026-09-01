const pdfFile = document.getElementById("pdfFile");
const analyzeBtn = document.getElementById("analyzeBtn");
const fileName = document.getElementById("fileName");
const loading = document.getElementById("loading");
const results = document.getElementById("results");


pdfFile.addEventListener("change", function () {

    if (pdfFile.files && pdfFile.files.length > 0) {
        fileName.textContent =
            "Selected: " + pdfFile.files[0].name;
    } else {
        fileName.textContent = "No file selected";
    }

});


analyzeBtn.addEventListener("click", analyzePDF);


function escapeHtml(value) {

    if (value === null || value === undefined) {
        return "";
    }

    const div = document.createElement("div");

    div.textContent = String(value);

    return div.innerHTML;
}


function getArray(value) {

    if (Array.isArray(value)) {
        return value;
    }

    return [];
}


function getNumber(value) {

    const number = Number(value);

    if (Number.isFinite(number)) {
        return number;
    }

    return 0;
}


function showEmpty(element, message) {

    element.innerHTML =
        `<p class="empty">${escapeHtml(message)}</p>`;
}


async function analyzePDF() {

    const file = pdfFile.files[0];

    if (!file) {
        alert("Please select a PDF file first.");
        return;
    }

    if (!file.name.toLowerCase().endsWith(".pdf")) {
        alert("Please select a valid PDF file.");
        return;
    }

    const formData = new FormData();

    formData.append("file", file);

    loading.style.display = "block";
    results.style.display = "none";

    analyzeBtn.disabled = true;
    analyzeBtn.textContent = "Analyzing...";

    try {

        const response = await fetch("/analyze", {
            method: "POST",
            body: formData
        });

        let responseData;

        try {
            responseData = await response.json();
        } catch (jsonError) {
            throw new Error(
                "Server returned an invalid response."
            );
        }

        if (!response.ok) {

            throw new Error(
                responseData.error ||
                "PDF analysis failed."
            );
        }

        if (responseData.success === false) {

            throw new Error(
                responseData.error ||
                "PDF analysis failed."
            );
        }

        const data =
            responseData.data ||
            responseData;

        console.log("PDF Analysis Result:", data);

        displayResults(data);

        results.style.display = "block";

        results.scrollIntoView({
            behavior: "smooth",
            block: "start"
        });

    } catch (error) {

        console.error("Analysis Error:", error);

        alert(
            "Analysis Error: " + error.message
        );

    } finally {

        loading.style.display = "none";

        analyzeBtn.disabled = false;

        analyzeBtn.textContent =
            "🔍 Analyze PDF";
    }

}


function displayResults(data) {

    if (!data || typeof data !== "object") {
        throw new Error("Invalid analysis data received.");
    }

    displayRiskBanner(data);
    displaySummary(data);

    displayRiskyWords(data);
    displaySuspiciousParagraphs(data);

    displayUrls(data);
    displayClickableLinks(data);

    displayImages(data);

    displayAttachments(data);

    displayFeatures(data);

    displayMetadata(data);

    displayPages(data);
}


function displayRiskBanner(data) {

    const summary = data.summary || {};

    const score = getNumber(
        summary.indicator_score ??
        data.indicator_score ??
        0
    );

    const riskyWords = getArray(
        data.risky_words
    );

    const paragraphs = getArray(
        data.suspicious_paragraphs
    );

    const urls = getArray(
        data.urls
    );

    const scoreElement =
        document.getElementById("riskScore");

    scoreElement.textContent = score;

    let status = "Low Risk";
    let description =
        "No major suspicious indicators detected.";

    if (score >= 8) {

        status = "High Risk";

        description =
            "Multiple suspicious indicators were detected. Review the flagged content carefully.";

        scoreElement.style.color = "#dc2626";

    } else if (score >= 4) {

        status = "Medium Risk";

        description =
            "Some suspicious indicators were detected and should be reviewed.";

        scoreElement.style.color = "#d97706";

    } else {

        scoreElement.style.color = "#16a34a";
    }

    document.getElementById(
        "riskStatus"
    ).textContent =
        summary.status || status;

    document.getElementById(
        "riskDescription"
    ).textContent =
        description +
        " Found " +
        riskyWords.length +
        " risky phrase matches, " +
        paragraphs.length +
        " suspicious sections and " +
        urls.length +
        " URLs.";
}


function displaySummary(data) {

    const summary = data.summary || {};

    const file = data.file || {};

    const riskyWords =
        getArray(data.risky_words);

    const paragraphs =
        getArray(data.suspicious_paragraphs);

    const urls =
        getArray(data.urls);

    const images =
        getArray(data.images);

    const attachments =
        getArray(data.attachments);

    const features =
        getArray(data.suspicious_features);

    const pages =
        getArray(data.pages);

    const pageCount =
        file.pages ??
        data.page_count ??
        pages.length ??
        0;

    document.getElementById(
        "summaryCards"
    ).innerHTML = `

        <div class="stat-card">
            <div class="stat-top">📄 Pages</div>
            <div class="stat-number">
                ${escapeHtml(pageCount)}
            </div>
        </div>

        <div class="stat-card">
            <div class="stat-top">🚨 Risky Phrases</div>
            <div class="stat-number">
                ${escapeHtml(
                    summary.total_risky_words ??
                    riskyWords.length
                )}
            </div>
        </div>

        <div class="stat-card">
            <div class="stat-top">🔍 Flagged Sections</div>
            <div class="stat-number">
                ${escapeHtml(
                    summary.total_suspicious_paragraphs ??
                    paragraphs.length
                )}
            </div>
        </div>

        <div class="stat-card">
            <div class="stat-top">🔗 URLs</div>
            <div class="stat-number">
                ${escapeHtml(
                    summary.total_urls ??
                    urls.length
                )}
            </div>
        </div>

        <div class="stat-card">
            <div class="stat-top">🖼️ Images</div>
            <div class="stat-number">
                ${escapeHtml(
                    summary.total_images ??
                    images.length
                )}
            </div>
        </div>

        <div class="stat-card">
            <div class="stat-top">⚠️ Indicators</div>
            <div class="stat-number">
                ${escapeHtml(
                    summary.total_features ??
                    features.length
                )}
            </div>
        </div>
    `;
}


function displayRiskyWords(data) {

    const container =
        document.getElementById("riskyWords");

    const items =
        getArray(data.risky_words);

    document.getElementById(
        "riskyCount"
    ).textContent =
        items.length + " found";

    if (items.length === 0) {

        showEmpty(
            container,
            "No risky words or suspicious phrases detected."
        );

        return;
    }

    container.innerHTML = "";

    items.forEach(function (item) {

        if (typeof item === "string") {

            container.innerHTML += `
                <div class="item danger-item">
                    <span class="keyword">
                        ${escapeHtml(item)}
                    </span>
                </div>
            `;

            return;
        }

        const pageText =
            item.page
                ? `Page ${escapeHtml(item.page)}`
                : "";

        container.innerHTML += `

            <div class="item danger-item">

                <div class="paragraph-meta">

                    <span class="category">
                        ${escapeHtml(
                            item.category ||
                            "Risk Indicator"
                        )}
                    </span>

                    ${pageText
                        ? `<span class="meta-tag">${pageText}</span>`
                        : ""
                    }

                </div>

                <div>

                    Detected:

                    <span class="keyword">
                        ${escapeHtml(
                            item.keyword ||
                            item.word ||
                            item.phrase ||
                            ""
                        )}
                    </span>

                </div>

                ${item.context
                    ? `
                        <div class="context">
                            ${escapeHtml(item.context)}
                        </div>
                    `
                    : ""
                }

            </div>
        `;
    });
}


function displaySuspiciousParagraphs(data) {

    const container =
        document.getElementById(
            "suspiciousParagraphs"
        );

    const items =
        getArray(
            data.suspicious_paragraphs
        );

    document.getElementById(
        "paragraphCount"
    ).textContent =
        items.length + " sections";

    if (items.length === 0) {

        showEmpty(
            container,
            "No suspicious text sections detected."
        );

        return;
    }

    container.innerHTML = "";

    items.forEach(function (item, index) {

        if (typeof item === "string") {

            container.innerHTML += `

                <div class="item warning-item">

                    <div class="paragraph-meta">
                        <span class="meta-tag">
                            Section ${index + 1}
                        </span>
                    </div>

                    <div class="paragraph-text">
                        ${escapeHtml(item)}
                    </div>

                </div>
            `;

            return;
        }

        let categories =
            getArray(item.categories);

        if (
            categories.length === 0 &&
            item.category
        ) {
            categories = [item.category];
        }

        const keywordList =
            getArray(item.keywords);

        container.innerHTML += `

            <div class="item warning-item">

                <div class="paragraph-meta">

                    <span class="meta-tag">
                        Page ${escapeHtml(
                            item.page || "?"
                        )}
                    </span>

                    <span class="meta-tag">
                        Section ${escapeHtml(
                            item.paragraph_number ||
                            index + 1
                        )}
                    </span>

                    <span class="meta-tag">
                        Risk Score:
                        ${escapeHtml(
                            item.risk_score ?? 0
                        )}
                    </span>

                    <span class="meta-tag">
                        ${escapeHtml(
                            categories.join(", ") ||
                            "Suspicious Content"
                        )}
                    </span>

                </div>

                ${keywordList.length > 0
                    ? `
                        <div class="context">
                            <strong>Matched:</strong>
                            ${escapeHtml(
                                keywordList.join(", ")
                            )}
                        </div>
                    `
                    : ""
                }

                <div class="paragraph-text">
                    ${escapeHtml(
                        item.text ||
                        item.paragraph ||
                        ""
                    )}
                </div>

            </div>
        `;
    });
}


function displayUrls(data) {

    const container =
        document.getElementById("urls");

    const items =
        getArray(data.urls);

    document.getElementById(
        "urlCount"
    ).textContent =
        items.length + " URLs";

    if (items.length === 0) {

        showEmpty(
            container,
            "No URLs found in the PDF."
        );

        return;
    }

    container.innerHTML = "";

    items.forEach(function (item) {

        const url =
            typeof item === "string"
                ? item
                : item.url;

        const page =
            typeof item === "object"
                ? item.page
                : "";

        const source =
            typeof item === "object"
                ? item.source
                : "";

        container.innerHTML += `

            <div class="item">

                ${page
                    ? `
                        <div class="paragraph-meta">
                            <span class="meta-tag">
                                Page ${escapeHtml(page)}
                            </span>

                            ${source
                                ? `
                                    <span class="meta-tag">
                                        ${escapeHtml(source)}
                                    </span>
                                `
                                : ""
                            }
                        </div>
                    `
                    : ""
                }

                <span class="url">
                    ${escapeHtml(url || "")}
                </span>

            </div>
        `;
    });
}


function displayClickableLinks(data) {

    const container =
        document.getElementById(
            "clickableLinks"
        );

    const items =
        getArray(
            data.clickable_links
        );

    document.getElementById(
        "clickableCount"
    ).textContent =
        items.length + " links";

    if (items.length === 0) {

        showEmpty(
            container,
            "No clickable links found."
        );

        return;
    }

    container.innerHTML = "";

    items.forEach(function (item) {

        const url =
            typeof item === "string"
                ? item
                : item.url;

        const page =
            typeof item === "object"
                ? item.page
                : "";

        container.innerHTML += `

            <div class="item">

                <div class="paragraph-meta">

                    <span class="meta-tag">
                        ${page
                            ? "Page " + escapeHtml(page)
                            : "Clickable Link"
                        }
                    </span>

                </div>

                <span class="url">
                    ${escapeHtml(url || "")}
                </span>

            </div>
        `;
    });
}


function displayImages(data) {

    const container =
        document.getElementById("images");

    const items =
        getArray(data.images);

    document.getElementById(
        "imageCount"
    ).textContent =
        items.length + " images";

    if (items.length === 0) {

        showEmpty(
            container,
            "No embedded images found."
        );

        return;
    }

    container.innerHTML = "";

    items.forEach(function (item, index) {

        if (!item || !item.data) {
            return;
        }

        const imageId =
            item.id || index + 1;

        const page =
            item.page || "Unknown";

        const width =
            item.width || "?";

        const height =
            item.height || "?";

        const format =
            item.format || "Unknown";

        /*
        Base64 image data comes directly from
        the backend. The image is displayed only
        in the browser and is not saved by JS.
        */

        const card =
            document.createElement("div");

        card.className =
            "image-card";

        const image =
            document.createElement("img");

        image.src = item.data;

        image.alt =
            "Extracted PDF image " + imageId;

        image.addEventListener(
            "click",
            function () {
                openImage(item.data);
            }
        );

        const info =
            document.createElement("div");

        info.className =
            "image-info";

        info.innerHTML = `
            <strong>
                Image ${escapeHtml(imageId)}
            </strong>

            <br>

            Page:
            ${escapeHtml(page)}

            <br>

            ${escapeHtml(width)}
            ×
            ${escapeHtml(height)}

            <br>

            ${escapeHtml(format)}
        `;

        card.appendChild(image);
        card.appendChild(info);

        container.appendChild(card);
    });

    if (container.children.length === 0) {

        showEmpty(
            container,
            "Images were detected but could not be displayed."
        );
    }
}


function displayAttachments(data) {

    const container =
        document.getElementById(
            "attachments"
        );

    const items =
        getArray(data.attachments);

    document.getElementById(
        "attachmentCount"
    ).textContent =
        items.length + " attachments";

    if (items.length === 0) {

        showEmpty(
            container,
            "No embedded attachments found."
        );

        return;
    }

    container.innerHTML = "";

    items.forEach(function (item) {

        const name =
            typeof item === "string"
                ? item
                : (
                    item.name ||
                    item.filename ||
                    "Unknown attachment"
                );

        container.innerHTML += `

            <div class="item warning-item">

                📎
                ${escapeHtml(name)}

            </div>
        `;
    });
}


function displayFeatures(data) {

    const container =
        document.getElementById("suspicious");

    const items =
        getArray(
            data.suspicious_features
        );

    document.getElementById(
        "featureCount"
    ).textContent =
        items.length + " indicators";

    if (items.length === 0) {

        showEmpty(
            container,
            "No suspicious PDF structure indicators detected."
        );

        return;
    }

    container.innerHTML = "";

    items.forEach(function (item) {

        if (typeof item === "string") {

            container.innerHTML += `

                <div class="item danger-item">
                    ${escapeHtml(item)}
                </div>
            `;

            return;
        }

        container.innerHTML += `

            <div class="item danger-item">

                <strong>
                    ${escapeHtml(
                        item.category ||
                        item.name ||
                        "PDF Indicator"
                    )}
                </strong>

                <br><br>

                ${escapeHtml(
                    item.description ||
                    item.keyword ||
                    ""
                )}

            </div>
        `;
    });
}


function displayMetadata(data) {

    const container =
        document.getElementById("metadata");

    const metadata =
        data.metadata || {};

    if (
        !metadata ||
        typeof metadata !== "object" ||
        Array.isArray(metadata) ||
        Object.keys(metadata).length === 0
    ) {

        showEmpty(
            container,
            "No metadata found."
        );

        return;
    }

    container.innerHTML = "";

    Object.entries(metadata).forEach(
        function ([key, value]) {

            let displayValue;

            if (
                value !== null &&
                typeof value === "object"
            ) {

                displayValue =
                    JSON.stringify(value);

            } else {

                displayValue =
                    String(value);
            }

            container.innerHTML += `

                <div class="item">

                    <strong>
                        ${escapeHtml(key)}
                    </strong>

                    <br><br>

                    ${escapeHtml(displayValue)}

                </div>
            `;
        }
    );
}


function displayPages(data) {

    const container =
        document.getElementById("pages");

    const items =
        getArray(data.pages);

    if (items.length === 0) {

        showEmpty(
            container,
            "No page statistics available."
        );

        return;
    }

    let html = `
        <table>

            <thead>
                <tr>
                    <th>Page</th>
                    <th>Words</th>
                    <th>Characters</th>
                </tr>
            </thead>

            <tbody>
    `;

    items.forEach(function (item, index) {

        html += `

            <tr>

                <td>
                    ${escapeHtml(
                        item.page || index + 1
                    )}
                </td>

                <td>
                    ${escapeHtml(
                        item.words ||
                        item.word_count ||
                        0
                    )}
                </td>

                <td>
                    ${escapeHtml(
                        item.characters ||
                        item.character_count ||
                        0
                    )}
                </td>

            </tr>
        `;
    });

    html += `
            </tbody>

        </table>
    `;

    container.innerHTML = html;
}


function openImage(imageSource) {

    const imageWindow =
        window.open(
            "",
            "_blank"
        );

    if (!imageWindow) {

        alert(
            "Unable to open image preview. Please allow popups."
        );

        return;
    }

    imageWindow.document.write(`
        <!DOCTYPE html>

        <html lang="en">

        <head>

            <meta charset="UTF-8">

            <title>
                Extracted PDF Image
            </title>

            <style>

                body {
                    margin: 0;
                    padding: 20px;

                    min-height: 100vh;

                    display: flex;
                    align-items: center;
                    justify-content: center;

                    background: #f8fafc;
                }

                img {
                    max-width: 100%;
                    max-height: 95vh;

                    object-fit: contain;

                    background: white;
                    border-radius: 10px;
                }

            </style>

        </head>

        <body>

            <img
                src="${imageSource}"
                alt="Extracted PDF image"
            >

        </body>

        </html>
    `);

    imageWindow.document.close();
}