from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
from database import get_db_connection

app = Flask(__name__)
app.secret_key = "smart-expense-tracker-secret"


@app.route("/")
def home():
    return redirect(url_for("login"))


# ---------------- REGISTER ----------------

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = generate_password_hash(request.form["password"])

        try:
            connection = get_db_connection()
            cursor = connection.cursor()

            query = """
                INSERT INTO users (name, email, password)
                VALUES (%s, %s, %s)
            """

            cursor.execute(query, (name, email, password))
            connection.commit()

            cursor.close()
            connection.close()

            return redirect(url_for("login"))

        except Exception as e:
            return f"Registration failed: {e}"

    return render_template("register.html")


# ---------------- LOGIN ----------------

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)

            cursor.execute("""
                SELECT *
                FROM users
                WHERE email = %s AND password = %s
            """, (email, password))

            user = cursor.fetchone()

            cursor.close()
            connection.close()

            if user:
                session["user_id"] = user["user_id"]
                session["user_name"] = user["name"]

                return redirect(url_for("dashboard"))

            return "Invalid email or password."

        except Exception as e:
            return f"Login failed: {e}"

    return render_template("login.html")

# ---------------- PROFILE ----------------

@app.route("/profile", methods=["GET", "POST"])
def profile():

    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    # Get current user
    cursor.execute("""
        SELECT user_id, name, email
        FROM users
        WHERE user_id = %s
    """, (user_id,))

    user = cursor.fetchone()

    if not user:
        cursor.close()
        connection.close()
        session.clear()
        return redirect(url_for("login"))

    # Update profile
    if request.method == "POST":

        name = request.form["name"].strip()
        password = request.form.get("password", "").strip()

        if not name:
            cursor.close()
            connection.close()
            return "Name cannot be empty."

        if password:

            cursor.execute("""
                UPDATE users
                SET name = %s,
                    password = %s
                WHERE user_id = %s
            """, (
                name,
                password,
                user_id
            ))

        else:

            cursor.execute("""
                UPDATE users
                SET name = %s
                WHERE user_id = %s
            """, (
                name,
                user_id
            ))

        connection.commit()

        # Update session name
        session["user_name"] = name

        cursor.close()
        connection.close()

        return redirect(url_for("profile"))

    cursor.close()
    connection.close()

    return render_template(
        "profile.html",
        user=user
    )

# ---------------- DASHBOARD ----------------

@app.route("/dashboard")
def dashboard():

    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        # Get user's budget
        cursor.execute("""
            SELECT COALESCE(SUM(amount), 0) AS budget
            FROM budgets
            WHERE user_id = %s
        """, (user_id,))

        budget_data = cursor.fetchone()
        budget = float(budget_data["budget"])

        # Get total expenses
        cursor.execute("""
            SELECT COALESCE(SUM(amount), 0) AS expenses
            FROM expenses
            WHERE user_id = %s
        """, (user_id,))

        expense_data = cursor.fetchone()
        total_expenses = float(expense_data["expenses"])

        remaining = budget - total_expenses

        # Recent expenses
        cursor.execute("""
            SELECT e.amount, e.expense_date, c.category_name
            FROM expenses e
            JOIN categories c
            ON e.category_id = c.category_id
            WHERE e.user_id = %s
            ORDER BY e.expense_date DESC
            LIMIT 5
        """, (user_id,))

        recent_expenses = cursor.fetchall()

        cursor.close()
        connection.close()

        return render_template(
            "dashboard.html",
            user_name=session["user_name"],
            budget=budget,
            total_expenses=total_expenses,
            remaining=remaining,
            recent_expenses=recent_expenses
        )

    except Exception as e:
        return f"Dashboard error: {e}"

@app.route("/add-expense", methods=["GET", "POST"])
def add_expense():

    if "user_id" not in session:
        return redirect(url_for("login"))

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    # Get all categories for dropdown
    cursor.execute("SELECT * FROM categories ORDER BY category_name")
    categories = cursor.fetchall()

    if request.method == "POST":

        amount = request.form["amount"]
        expense_date = request.form["expense_date"]
        category_id = request.form["category_id"]

        # Basic validation
        try:
            amount = float(amount)

            if amount <= 0:
                return "Amount must be greater than 0."

        except ValueError:
            return "Please enter a valid amount."

        # Insert expense
        cursor.execute("""
            INSERT INTO expenses
            (amount, expense_date, category_id, user_id)
            VALUES (%s, %s, %s, %s)
        """, (
            amount,
            expense_date,
            category_id,
            session["user_id"]
        ))

        connection.commit()

        cursor.close()
        connection.close()

        return redirect(url_for("dashboard"))

    cursor.close()
    connection.close()

    return render_template(
        "add_expense.html",
        categories=categories
    )
@app.route("/expenses")
def expenses():

    if "user_id" not in session:
        return redirect(url_for("login"))

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            e.expense_id,
            e.amount,
            e.expense_date,
            c.category_name
        FROM expenses e
        JOIN categories c
            ON e.category_id = c.category_id
        WHERE e.user_id = %s
        ORDER BY e.expense_date DESC, e.expense_id DESC
    """, (session["user_id"],))

    expenses = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template(
        "expenses.html",
        expenses=expenses
    )
@app.route("/edit-expense/<int:expense_id>", methods=["GET", "POST"])
def edit_expense(expense_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    # Get the expense belonging to the logged-in user
    cursor.execute("""
        SELECT *
        FROM expenses
        WHERE expense_id = %s
        AND user_id = %s
    """, (expense_id, session["user_id"]))

    expense = cursor.fetchone()

    if not expense:
        cursor.close()
        connection.close()
        return "Expense not found."

    # Get categories
    cursor.execute("""
        SELECT *
        FROM categories
        ORDER BY category_name
    """)

    categories = cursor.fetchall()

    if request.method == "POST":

        amount = request.form["amount"]
        expense_date = request.form["expense_date"]
        category_id = request.form["category_id"]

        try:
            amount = float(amount)

            if amount <= 0:
                return "Amount must be greater than 0."

        except ValueError:
            return "Please enter a valid amount."

        cursor.execute("""
            UPDATE expenses
            SET amount = %s,
                expense_date = %s,
                category_id = %s
            WHERE expense_id = %s
            AND user_id = %s
        """, (
            amount,
            expense_date,
            category_id,
            expense_id,
            session["user_id"]
        ))

        connection.commit()

        cursor.close()
        connection.close()

        return redirect(url_for("expenses"))

    cursor.close()
    connection.close()

    return render_template(
        "edit_expense.html",
        expense=expense,
        categories=categories
    )
@app.route("/delete-expense/<int:expense_id>", methods=["POST"])
def delete_expense(expense_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("""
        DELETE FROM expenses
        WHERE expense_id = %s
        AND user_id = %s
    """, (
        expense_id,
        session["user_id"]
    ))

    connection.commit()

    cursor.close()
    connection.close()

    return redirect(url_for("expenses"))
@app.route("/budget", methods=["GET", "POST"])
def budget():

    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    if request.method == "POST":

        amount = request.form["amount"]
        budget_type = request.form["budget_type"]

        try:
            amount = float(amount)

            if amount <= 0:
                return "Budget amount must be greater than 0."

        except ValueError:
            return "Please enter a valid budget amount."

        # Check whether a budget already exists
        cursor.execute("""
            SELECT budget_id
            FROM budgets
            WHERE user_id = %s
        """, (user_id,))

        existing_budget = cursor.fetchone()

        if existing_budget:

            cursor.execute("""
                UPDATE budgets
                SET amount = %s,
                    budget_type = %s
                WHERE budget_id = %s
                AND user_id = %s
            """, (
                amount,
                budget_type,
                existing_budget["budget_id"],
                user_id
            ))

        else:

            cursor.execute("""
                INSERT INTO budgets
                (amount, budget_type, user_id)
                VALUES (%s, %s, %s)
            """, (
                amount,
                budget_type,
                user_id
            ))

        connection.commit()

    # Get current budget
    cursor.execute("""
        SELECT *
        FROM budgets
        WHERE user_id = %s
        LIMIT 1
    """, (user_id,))

    budget_data = cursor.fetchone()

    if budget_data:
        budget_amount = float(budget_data["amount"])
        budget_type = budget_data["budget_type"]
    else:
        budget_amount = 0
        budget_type = "monthly"

    # Calculate total expenses
    cursor.execute("""
        SELECT COALESCE(SUM(amount), 0) AS total_expenses
        FROM expenses
        WHERE user_id = %s
    """, (user_id,))

    expense_data = cursor.fetchone()
    total_expenses = float(expense_data["total_expenses"])

    remaining = budget_amount - total_expenses

    # Determine alert status
    if budget_amount == 0:
        alert = "No budget has been set yet."

    elif total_expenses >= budget_amount:
        alert = "Budget Exceeded!"

    elif total_expenses >= budget_amount * 0.8:
        alert = "Warning: You have used 80% or more of your budget."

    else:
        alert = "You are within your budget."

    cursor.close()
    connection.close()

    return render_template(
        "budget.html",
        budget_amount=budget_amount,
        budget_type=budget_type,
        total_expenses=total_expenses,
        remaining=remaining,
        alert=alert
    )

# ---------------- REPORTS ----------------

@app.route("/reports")
def reports():

    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    # Total expenses
    cursor.execute("""
        SELECT COALESCE(SUM(amount), 0) AS total
        FROM expenses
        WHERE user_id = %s
    """, (user_id,))

    total_data = cursor.fetchone()
    total_expenses = float(total_data["total"])


    # Category-wise expenses
    cursor.execute("""
        SELECT
            c.category_name,
            COALESCE(SUM(e.amount), 0) AS total
        FROM expenses e
        JOIN categories c
            ON e.category_id = c.category_id
        WHERE e.user_id = %s
        GROUP BY c.category_id, c.category_name
        ORDER BY total DESC
    """, (user_id,))

    category_data = cursor.fetchall()

    # Convert Decimal to float
    for item in category_data:
        item["total"] = float(item["total"])


    cursor.close()
    connection.close()


    categories = [
        item["category_name"]
        for item in category_data
    ]

    category_amounts = [
        item["total"]
        for item in category_data
    ]


    return render_template(
        "reports.html",
        total_expenses=total_expenses,
        category_data=category_data,
        categories=categories,
        category_amounts=category_amounts
    )
# ---------------- LOGOUT ----------------

@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("login"))


if __name__ == "__main__":
    app.run(debug=True)