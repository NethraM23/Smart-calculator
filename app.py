
from flask import Flask, render_template, request, jsonify
import ast
import math
import operator
import re
import sqlite3

app = Flask(__name__)

# Keep the database in the same folder as app.py
DATABASE = "calculator.db"


def get_connection():
    return sqlite3.connect(
        __import__("os").path.join(app.root_path, DATABASE)
    )


def create_database():
    with get_connection() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                problem TEXT,
                answer TEXT
            )
        """)


def format_number(number):
    """Display whole numbers without unnecessary .0."""
    if isinstance(number, float) and number.is_integer():
        return str(int(number))
    return str(number)


def safe_evaluate(expression):
    """
    Safely evaluate mathematical expressions using Python's AST.
    Only numeric constants, brackets, unary signs, and approved
    mathematical operators are allowed.
    """
    if not expression or len(expression) > 200:
        raise ValueError("Invalid expression")

    try:
        tree = ast.parse(expression, mode="eval")
    except (SyntaxError, ValueError, RecursionError):
        raise ValueError("Invalid mathematical expression")

    steps = []

    binary_operations = {
        ast.Add: (operator.add, "+"),
        ast.Sub: (operator.sub, "-"),
        ast.Mult: (operator.mul, "×"),
        ast.Div: (operator.truediv, "÷"),
        ast.Pow: (operator.pow, "**"),
    }

    unary_operations = {
        ast.UAdd: operator.pos,
        ast.USub: operator.neg,
    }

    def evaluate(node):
        if isinstance(node, ast.Expression):
            return evaluate(node.body)

        # Accept numbers only, not strings or Boolean values.
        if isinstance(node, ast.Constant):
            if type(node.value) not in (int, float):
                raise ValueError("Only numbers are allowed")

            if abs(node.value) > 1e100:
                raise ValueError("Number is too large")

            return node.value

        # Support negative and positive numbers, e.g. -5 + 2.
        if isinstance(node, ast.UnaryOp):
            operation = unary_operations.get(type(node.op))

            if operation is None:
                raise ValueError("Unsupported operator")

            value = evaluate(node.operand)
            result = operation(value)
            return check_result(result)

        if isinstance(node, ast.BinOp):
            operation_info = binary_operations.get(type(node.op))

            if operation_info is None:
                raise ValueError("Unsupported operator")

            left = evaluate(node.left)
            right = evaluate(node.right)
            operation, symbol = operation_info

            if isinstance(node.op, ast.Div) and right == 0:
                raise ValueError("Cannot divide by zero")

            # Limit powers to avoid excessive computation.
            if isinstance(node.op, ast.Pow):
                if abs(right) > 100 or abs(left) > 1e100:
                    raise ValueError("Power is too large")

            result = check_result(operation(left, right))

            steps.append(
                f"{format_number(left)} {symbol} "
                f"{format_number(right)} = {format_number(result)}"
            )

            return result

        # Reject names, function calls, imports, and other Python syntax.
        raise ValueError("Only mathematical expressions are allowed")

    try:
        answer = evaluate(tree)
    except (ArithmeticError, OverflowError, RecursionError) as error:
        raise ValueError("Invalid mathematical calculation") from error

    return answer, steps


def check_result(result):
    if type(result) not in (int, float):
        raise ValueError("Invalid result")

    if not math.isfinite(result):
        raise ValueError("Result is too large")

    if abs(result) > 1e100:
        raise ValueError("Result is too large")

    return result


def save_history(problem, answer):
    with get_connection() as connection:
        connection.execute(
            "INSERT INTO history (problem, answer) VALUES (?, ?)",
            (problem, str(answer))
        )


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/solve", methods=["POST"])
def solve():
    data = request.get_json(silent=True) or {}
    problem = data.get("problem", "")

    if not isinstance(problem, str):
        return jsonify({
            "error": "Invalid mathematical problem."
        }), 400

    expression = problem.replace(" ", "")

    if not expression or len(expression) > 200:
        return jsonify({
            "error": "Enter a valid mathematical problem."
        }), 400

    try:
        # Percentage: 20%200 means 20 percent of 200.
        percentage_pattern = (
            r"^([+-]?(?:\d+(?:\.\d*)?|\.\d+))%"
            r"([+-]?(?:\d+(?:\.\d*)?|\.\d+))$"
        )

        percentage_match = re.fullmatch(
            percentage_pattern, expression
        )

        if "%" in expression:
            if not percentage_match:
                raise ValueError("Invalid percentage expression")

            percentage = float(percentage_match.group(1))
            number = float(percentage_match.group(2))

            step1 = percentage / 100
            result = check_result(step1 * number)

            steps = [
                f"{format_number(percentage)} ÷ 100 = "
                f"{format_number(step1)}",
                f"{format_number(step1)} × "
                f"{format_number(number)} = "
                f"{format_number(result)}"
            ]

        else:
            result, steps = safe_evaluate(expression)

        answer = (
            int(result)
            if isinstance(result, float) and result.is_integer()
            else result
        )

        # Include the original expression and final result when needed.
        if not steps or steps[-1].split(" = ")[-1] != format_number(answer):
            steps.append(
                f"{problem} = {format_number(answer)}"
            )

        save_history(problem, answer)

        return jsonify({
            "problem": problem,
            "steps": steps,
            "answer": answer
        })

    except (ValueError, ArithmeticError, OverflowError, RecursionError):
        return jsonify({
            "error": "Invalid mathematical problem."
        }), 400


@app.route("/history")
def history():
    with get_connection() as connection:
        records = connection.execute(
            "SELECT problem, answer FROM history ORDER BY id DESC"
        ).fetchall()

    return jsonify(records)


@app.route("/clear-history", methods=["POST"])
def clear_history():
    with get_connection() as connection:
        connection.execute("DELETE FROM history")

    return jsonify({
        "message": "History cleared"
    })


if __name__ == "__main__":
    create_database()
    app.run(debug=True)
