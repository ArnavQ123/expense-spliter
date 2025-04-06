import streamlit as st
import requests
import json
import random
import pandas as pd
from datetime import datetime
from time import time as t

# Replace with your actual On-Demand API key
ON_DEMAND_API_KEY = "OhxY9mOtD7nIX1Uwk28pfvfjWZ1NCLHH"

# Function to interact with the On-Demand API
def query_ai(session_id, prompt, custom_instructions=None):
    """Query the On-Demand API with the given prompt"""
    start_time = t()
    
    url = f"https://api.on-demand.io/chat/v1/sessions/{session_id}/query"
    
    # Combine custom instructions with the prompt if provided
    if custom_instructions:
        query_text = f"{custom_instructions}\n\n{prompt}"
    else:
        query_text = prompt
    
    payload = {
        "responseMode": "sync",
        "endpointId": "predefined-openai-gpt4o",  # Using GPT-4o as the model
        "query": query_text
    }
    
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "apikey": ON_DEMAND_API_KEY
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        response_data = json.loads(response.text)
        return response_data["data"]["answer"], t() - start_time
    except Exception as e:
        return f"Error: {e}", t() - start_time

# Initialize API session
def initialize_api_session():
    """Initialize a new On-Demand API session"""
    if 'session_id' not in st.session_state:
        # Generate random user ID
        user_id = f"user_{random.randint(1000, 9999)}"
        
        # Create a new chat session with On-Demand API
        url = "https://api.on-demand.io/chat/v1/sessions"
        payload = {"externalUserId": user_id}
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "apikey": ON_DEMAND_API_KEY
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers)
            response_data = json.loads(response.text)
            st.session_state.session_id = response_data["data"]["id"]
            
            # Pre-train the AI to act as an expense manager
            system_prompt = """You are an expense management assistant. 
            Your job is to help users track expenses, split payments, and provide financial insights.
            When analyzing expenses:
            1. Calculate per-person totals and who owes whom
            2. Identify spending patterns and categories
            3. Provide brief, actionable financial insights
            4. Respond in a concise, friendly manner
            """
            
            query_ai(st.session_state.session_id, "Initialize as expense manager", system_prompt)
            return True
        except Exception as e:
            st.error(f"Failed to initialize API session: {e}")
            return False
    return True

# Initialize state variables
def initialize_state():
    """Initialize session state variables if they don't exist"""
    if 'expenses' not in st.session_state:
        st.session_state.expenses = []
    if 'people' not in st.session_state:
        st.session_state.people = set()
    if 'tab' not in st.session_state:
        st.session_state.tab = "Add Expense"
    if 'summary' not in st.session_state:
        st.session_state.summary = None

# Functions for expense management
def add_expense(description, amount, paid_by, split_among, date):
    """Add a new expense to the list"""
    # Calculate split amount
    split_amount = amount / len(split_among)
    
    # Create expense record
    expense = {
        "id": len(st.session_state.expenses) + 1,
        "description": description,
        "amount": amount,
        "paid_by": paid_by,
        "split_among": split_among,
        "date": date,
        "split_amount": split_amount
    }
    
    st.session_state.expenses.append(expense)
    
    # Update people set
    st.session_state.people.add(paid_by)
    for person in split_among:
        st.session_state.people.add(person)
    
    # Clear the summary to force regeneration
    st.session_state.summary = None

def delete_expense(expense_id):
    """Delete an expense from the list"""
    st.session_state.expenses = [e for e in st.session_state.expenses if e["id"] != expense_id]
    
    # Rebuild the people set based on remaining expenses
    st.session_state.people = set()
    for expense in st.session_state.expenses:
        st.session_state.people.add(expense["paid_by"])
        for person in expense["split_among"]:
            st.session_state.people.add(person)
    
    # Clear the summary to force regeneration
    st.session_state.summary = None

def get_ai_summary():
    """Generate an AI summary of the expenses"""
    if not st.session_state.expenses:
        return "No expenses to analyze yet."
    
    # Prepare expense data for the AI
    expense_data = []
    for e in st.session_state.expenses:
        expense_data.append({
            "description": e["description"],
            "amount": e["amount"],
            "paid_by": e["paid_by"],
            "split_among": ", ".join(e["split_among"]),
            "date": e["date"].strftime("%Y-%m-%d")
        })
    
    # Convert to string format
    expenses_str = json.dumps(expense_data, indent=2)
    
    # Create prompt for the AI
    prompt = f"""
    Analyze these expenses and provide:
    1. A summary of who owes whom and how much
    2. Total spent per person
    3. Minimum number of transactions needed to settle all debts
    4. Brief insights on spending patterns if any
    
    Expenses data:
    {expenses_str}
    """
    
    # Query the AI
    if 'session_id' in st.session_state:
        summary, _ = query_ai(st.session_state.session_id, prompt)
        return summary
    else:
        return "AI service not connected."

# UI Components
def create_sidebar():
    """Create sidebar with options"""
    with st.sidebar:
        st.title("💰 SplitWise AI ")
        
        # Navigation
        st.subheader("Navigation \n")

        if st.button("➕ Add Expense", use_container_width=True):
            st.session_state.tab = "Add Expense"
        if st.button("📊 View Expenses", use_container_width=True):
            st.session_state.tab = "View Expenses"
        if st.button("🧠 AI Summary", use_container_width=True):
            st.session_state.tab = "AI Summary"
        
        # API status
        st.divider()
        st.subheader("AI Connection")
        if 'session_id' in st.session_state:
            st.success("Connected to AI Service")
            session_id = st.session_state.session_id
            st.caption(f"Session ID: {session_id[:10]}...")
            
            if st.button("Reset AI Session", use_container_width=True):
                if 'session_id' in st.session_state:
                    del st.session_state.session_id
                st.rerun()
        else:
            st.error("Not connected to AI")
            if st.button("Connect", use_container_width=True):
                if initialize_api_session():
                    st.success("Connected!")
                    st.rerun()
        
        # App info
        st.divider()
        st.subheader("project by ")
        st.caption("Arnav (12308643) ")
        st.caption("yusuf (12305692) ")
        st.caption("Ashmit (12313815)")

def render_add_expense():
    """Render the add expense form"""
    st.header("Add New Expense")
    
    with st.form("expense_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            description = st.text_input("Description", placeholder="Dinner, Movie tickets, etc.")
            amount = st.number_input("Amount", min_value=0.01, format="%.2f")
            date = st.date_input("Date", datetime.now())
        
        with col2:
            # If we have people already, use them as suggestions
            people_list = list(st.session_state.people)
            
            # For paid by, use a selectbox if we have people, otherwise text input
            if people_list:
                new_person_option = "➕ Add new person"
                paid_by_options = people_list + [new_person_option]
                paid_by_selection = st.selectbox("Paid by", options=paid_by_options)
                
                if paid_by_selection == new_person_option:
                    paid_by = st.text_input("Enter name", key="new_paid_by")
                else:
                    paid_by = paid_by_selection
            else:
                paid_by = st.text_input("Paid by", placeholder="Enter name")
            
            # For split among, use multiselect with option to add new
            if people_list:
                split_among_options = people_list
                split_among = st.multiselect("Split among", options=split_among_options, default=split_among_options)
                
                # Option to add a new person to split among
                add_new_splitter = st.checkbox("Add another person to split with")
                if add_new_splitter:
                    new_splitter = st.text_input("Enter name", key="new_splitter")
                    if new_splitter and new_splitter not in split_among:
                        split_among.append(new_splitter)
            else:
                split_names = st.text_input("Split among (comma separated)", placeholder="Alice, Bob, Charlie")
                split_among = [name.strip() for name in split_names.split(",")] if split_names else []
        
        submit = st.form_submit_button("Add Expense", use_container_width=True)
        
        if submit:
            # Validate inputs
            if not description:
                st.error("Please enter a description")
            elif amount <= 0:
                st.error("Amount must be greater than 0")
            elif not paid_by:
                st.error("Please enter who paid")
            elif not split_among:
                st.error("Please enter at least one person to split with")
            else:
                # Add the expense
                add_expense(description, amount, paid_by, split_among, date)
                st.success(f"Added expense: {description} (${amount:.2f})")
                st.rerun()

def render_view_expenses():
    """Render the expenses view"""
    st.header("Expense List")
    
    if not st.session_state.expenses:
        st.info("No expenses added yet. Add some expenses to get started!")
        return
    
    # Create a DataFrame for display
    df_data = []
    for expense in st.session_state.expenses:
        df_data.append({
            "ID": expense["id"],
            "Date": expense["date"].strftime("%Y-%m-%d"),
            "Description": expense["description"],
            "Amount": f"${expense['amount']:.2f}",
            "Paid By": expense["paid_by"],
            "Split Among": ", ".join(expense["split_among"]),
            "Per Person": f"${expense['split_amount']:.2f}"
        })
    
    df = pd.DataFrame(df_data)
    
    # Filter options
    st.subheader("Filters")
    col1, col2 = st.columns(2)
    
    with col1:
        person_filter = st.selectbox(
            "Filter by person", 
            options=["All"] + list(st.session_state.people)
        )
    
    with col2:
        min_amount = st.number_input("Minimum Amount", min_value=0.0, format="%.2f")
    
    # Apply filters
    filtered_df = df
    if person_filter != "All":
        filtered_df = filtered_df[
            (filtered_df["Paid By"] == person_filter) | 
            (filtered_df["Split Among"].str.contains(person_filter))
        ]
    
    if min_amount > 0:
        filtered_df = filtered_df[filtered_df["Amount"].str.replace("$", "").astype(float) >= min_amount]
    
    # Display the expenses
    st.divider()
    st.dataframe(filtered_df, use_container_width=True)
    
    # Delete option
    st.subheader("Delete Expense")
    delete_id = st.number_input("Enter expense ID to delete", min_value=1, max_value=len(st.session_state.expenses) if st.session_state.expenses else 1)
    if st.button("Delete", use_container_width=True):
        delete_expense(delete_id)
        st.success(f"Deleted expense #{delete_id}")
        st.rerun()

def render_ai_summary():
    """Render the AI summary view"""
    st.header("AI-Powered Expense Analysis")
    
    if not st.session_state.expenses:
        st.info("No expenses to analyze yet. Add some expenses to get started!")
        return
    
    # Generate or retrieve summary
    if st.session_state.summary is None or st.button("Refresh Analysis", use_container_width=True):
        with st.spinner("Analyzing expenses..."):
            st.session_state.summary = get_ai_summary()
    
    # Display summary
    st.divider()
    st.markdown(st.session_state.summary)
    
    # Allow asking specific questions
    st.divider()
    st.subheader("Ask a specific question")
    question = st.text_input("Your question about these expenses", placeholder="Who owes the most?")
    
    if st.button("Get Answer", use_container_width=True) and question:
        with st.spinner("Thinking..."):
            # Prepare context
            expense_data = []
            for e in st.session_state.expenses:
                expense_data.append({
                    "description": e["description"],
                    "amount": e["amount"],
                    "paid_by": e["paid_by"],
                    "split_among": ", ".join(e["split_among"]),
                    "date": e["date"].strftime("%Y-%m-%d")
                })
            
            context = f"""
            Based on these expenses:
            {json.dumps(expense_data, indent=2)}
            
            Answer this question: {question}
            """
            
            response, time_taken = query_ai(st.session_state.session_id, context)
            
            st.info(f"Response (in {time_taken:.2f}s):")
            st.markdown(response)

# Main App
def main():
    st.set_page_config(
        page_title="SplitWise AI",
        page_icon="💰",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Initialize state
    initialize_state()
    
    # Create sidebar
    create_sidebar()
    
    # Initialize API session if needed
    api_connected = 'session_id' in st.session_state or initialize_api_session()
    
    # Render the selected tab
    if st.session_state.tab == "Add Expense":
        render_add_expense()
    elif st.session_state.tab == "View Expenses":
        render_view_expenses()
    elif st.session_state.tab == "AI Summary":
        if api_connected:
            render_ai_summary()
        else:
            st.error("AI service not connected. Please connect in the sidebar.")

if __name__ == "__main__":
    main()
