function addValue(value) {

    document.getElementById("problem").value += value;
}


function clearInput() {

    document.getElementById("problem").value = "";
}

function deleteLast() {

    let input = document.getElementById("problem");

    input.value = input.value.slice(0, -1);
}

function solveProblem() {

    let problem = document.getElementById("problem").value;

    if (problem == "") {
        document.getElementById("steps").innerHTML =
            "Please enter a problem.";
        return;
    }

    fetch("/solve", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            problem: problem
        })
    })
    .then(response => response.json())
    .then(data => {

        if (data.error) {
            document.getElementById("steps").innerHTML =
                data.error;
            return;
        }

        let output =
            "<b>Problem:</b> " + data.problem + "<br><br>";

        for (let i = 0; i < data.steps.length; i++) {
            output +=
                "<b>Step " + (i + 1) + ":</b> " +
                data.steps[i] + "<br><br>";
        }

        output +=
            "<b>Final Answer: " +
            data.answer +
            "</b>";

        document.getElementById("steps").innerHTML = output;

        loadHistory();
    });
}


function loadHistory() {

    fetch("/history")
    .then(response => response.json())
    .then(data => {

        let historyList =
            document.getElementById("historyList");

        if (data.length == 0) {
            historyList.innerHTML =
                "No calculations yet.";
            return;
        }

        let output = "";

        for (let i = 0; i < data.length; i++) {

            output +=
                "<p>" +
                data[i][0] +
                " = " +
                data[i][1] +
                "</p>";
        }

        historyList.innerHTML = output;
    });
}


function clearHistory() {

    fetch("/clear-history", {
        method: "POST"
    })
    .then(response => response.json())
    .then(data => {

        document.getElementById("historyList").innerHTML =
            "No calculations yet.";
    });
}


loadHistory();