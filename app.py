from flask import Flask, render_template, request, redirect, url_for
import pandas as pd
import plotly.graph_objs as go
import matplotlib.pyplot as plt
import io
import base64

app = Flask(__name__)


# Function to generate the interactive pie chart
def generate_pie_chart(data):
    product_amounts = data.groupby('Product_Type')['Amount'].sum().reset_index()

    # Create a Plotly pie chart
    fig = go.Figure(data=[go.Pie(labels=product_amounts['Product_Type'], values=product_amounts['Amount'],
                                 hoverinfo='label+percent+value', textinfo='value',
                                 textposition='inside', hole=0.3)])
    return fig.to_html(full_html=False)


# Function to count occurrences of each product type in the specified lab
def count_product_types_in_lab(lab_number, data):
    # Filter data for the specified lab number
    lab_data = data[data['Lab'] == lab_number]
    
    # Count occurrences of each product type in the lab
    product_type_counts = lab_data['Product_Type'].value_counts()
    
    return product_type_counts

# Function to generate the Plotly graph for total number of items in each lab
def generate_lab_counts_graph(data):
    allowed_product_types = ['Desktop', 'Printer', 'Projector', 'Monitor', 'CPU']
    filtered_data = data[data['Product_Type'].isin(allowed_product_types)]
    lab_counts = filtered_data.groupby(['Lab', 'Product_Type'])['Qty'].sum().unstack(fill_value=0)

    if lab_counts.empty:
        return None
    else:
        traces = []
        for product_type in lab_counts.columns:
            traces.append(go.Bar(x=lab_counts.index, y=lab_counts[product_type], name=product_type))

        layout = go.Layout(title='Total Number of Items in Each Lab (Desktop, Printer, Projector, Monitor, CPU)',
                           xaxis=dict(title='Lab', tickvals=lab_counts.index), yaxis=dict(title='Total Number of Items'), barmode='stack')

        return go.Figure(data=traces, layout=layout).to_html(full_html=False)

# Function to calculate total amount for each product type
def calculate_total_amount_per_product(data):
    total_amount_per_product = data.groupby('Product_Type')['Amount'].sum()
    return total_amount_per_product

@app.route('/')
def index():
    # Read the CSV file into a DataFrame
    data = pd.read_csv("data_bap.csv", encoding='latin1')

    # Convert 'Date' column to datetime type, specifying the format and handling errors
    data['Date'] = pd.to_datetime(data['Date'], format='%d-%m-%Y', errors='coerce')

    # Drop rows with invalid dates (if any)
    data = data.dropna(subset=['Date'])

    # Extract year from 'Date' column
    data['Year'] = data['Date'].dt.year

    # Group by year and sum up the 'Amount' column
    yearly_amount_investment = data.groupby('Year')['Amount'].sum()

    # Plotly trace for the line chart
    trace = go.Scatter(x=yearly_amount_investment.index, y=yearly_amount_investment.values,
                       mode='lines+markers', marker=dict(color='skyblue'), name='Amount Invested')
    layout = go.Layout(title='Amount Invested Every Year', xaxis=dict(title='Year',tickvals=yearly_amount_investment.index,), yaxis=dict(title='Amount Invested (in Rs)'),)
    plot_div = go.Figure(data=[trace], layout=layout).to_html(full_html=False)

    # Generate the new graph for total number of items in each lab
    lab_counts_graph = generate_lab_counts_graph(data)

    # Dropdown menu options
    lab_options = [str(i) for i in range(1, 11)]

     # Generate the pie chart
    pie_chart = generate_pie_chart(data)

    return render_template('index.html', plot_div=plot_div, lab_options=lab_options, lab_counts_graph=lab_counts_graph, pie_chart=pie_chart)

# Route for handling lab selection
@app.route('/lab', methods=['POST'])
def lab():
    lab_number = request.form['lab']
    lab_options = [str(i) for i in range(1, 11)]
    # Read the CSV file into a DataFrame
    data = pd.read_csv("data_bap.csv", encoding='latin1')

    product_type_counts = count_product_types_in_lab(int(lab_number), data)
    
    pie_data = data[data['Lab'] == int(lab_number)]
    # Plotly trace for the bar chart
    trace = go.Bar(x=product_type_counts.index, y=product_type_counts.values, marker=dict(color='skyblue'))
    layout = go.Layout(title='Product Type Counts for Lab {}'.format(lab_number), xaxis=dict(title='Product Type'), yaxis=dict(title='Count'))
    plot_div = go.Figure(data=[trace], layout=layout).to_html(full_html=False)

    # Generate Matplotlib plot (if needed)
    allowed_product_types = ['Desktop', 'Printer', 'Projector', 'Monitor', 'CPU']
    filtered_data = data[data['Product_Type'].isin(allowed_product_types)]
    lab_counts = filtered_data.groupby('Lab')['Qty'].sum()
    if len(lab_counts) == 0:
        matplot_img = None
    else:
        plt.figure(figsize=(10, 6))
        lab_counts.plot(kind='bar', color='skyblue')
        plt.title('Total Number of Items in Each Lab (Desktop, Printer, Projector, Monitor)')
        plt.xlabel('Lab')
        plt.ylabel('Total Number of Items')
        plt.xticks(rotation=0)
        plt.tight_layout()

        # Save the Matplotlib plot as a PNG image
        img = io.BytesIO()
        plt.savefig(img, format='png')
        img.seek(0)
        matplot_img = base64.b64encode(img.getvalue()).decode()

    # Calculate total amount for each product
    total_amount_per_product = calculate_total_amount_per_product(data)

    # Plotly trace for the bar chart of total amount per product
    trace_total_amount = go.Bar(x=total_amount_per_product.index, y=total_amount_per_product.values, marker=dict(color='orange'))
    layout_total_amount = go.Layout(title='Total Amount for Each Product', xaxis=dict(title='Product Type'), yaxis=dict(title='Total Amount'))
    total_amount_plot_div = go.Figure(data=[trace_total_amount], layout=layout_total_amount).to_html(full_html=False)

     # Generate the pie chart
    pie_chart = generate_pie_chart(pie_data)

    return render_template('lab.html', plot_div=plot_div, lab_number=lab_number, total_amount_plot_div=total_amount_plot_div, matplot_img=matplot_img, pie_chart=pie_chart, lab_options=lab_options)




# Route for the admin page
@app.route('/admin')
def admin():
    # Read the CSV file into a DataFrame
    data = pd.read_csv("data_bap.csv", encoding='latin1')
    
    # Calculate total inventory stats
    inventory_stats = data['Product_Type'].value_counts()
    
    # Convert DataFrame to HTML table
    data_html = data.to_html(classes='table table-striped', index=False)
    
    # Pass the data to the HTML template
    return render_template('admin.html', data=data_html, inventory_stats=inventory_stats)

# Route for adding a new entry
@app.route('/add_entry', methods=['POST'])
def add_entry():
    # Read the original CSV file into a DataFrame
    data = pd.read_csv("data_bap.csv", encoding='latin1')

    # Retrieve data from the form
    sr = request.form['sr']
    description = request.form['description']
    qty = request.form['qty']
    date = request.form['date']
    supplier = request.form['supplier']
    main = request.form['main']
    lab = request.form['lab']
    amount = request.form['amount']
    product_type = request.form['product_type']
    remarks = request.form['remarks']

    # Add the new entry to the DataFrame
    new_entry = {'Sr': sr, 'Description': description, 'Qty': qty, 'Date': date,
                 'Supplier': supplier, 'Main': main, 'Lab': lab, 'Amount': amount,
                 'Product_Type': product_type, 'Remarks': remarks}
    data = data._append(new_entry, ignore_index=True)

    # Save the updated DataFrame to the same CSV file
    data.to_csv("data_bap.csv", index=False)

    # Redirect back to the admin page after adding the entry
    return redirect(url_for('admin'))

# Route for deleting an entry
@app.route('/delete_entry', methods=['POST'])
def delete_entry():
    # Retrieve SR number from the form
    sr_number = request.form['sr']

    # Load the CSV file into a DataFrame
    data = pd.read_csv("data_bap.csv", encoding='latin1')

    # Delete the row with the specified SR number
    data = data[data['Sr'] != int(sr_number)]

    # Save the updated DataFrame back to the CSV file
    data.to_csv("data_bap.csv", index=False)

    # Redirect back to the admin page after deleting the entry
    return redirect(url_for('admin'))



# Route for handling search
@app.route('/search', methods=['POST'])
def search():
    # Retrieve search query from the form
    search_query = request.form['searchQuery']

    # Read the CSV file into a DataFrame
    data = pd.read_csv("data_bap.csv", encoding='latin1')

    # Filter the data based on search query
    search_results = data[data.apply(lambda row: search_query.lower() in row.astype(str).str.lower().values, axis=1)]

    # Convert DataFrame to HTML table
    search_results_html = search_results.to_html(classes='table table-striped', index=False)

    return render_template('search_results.html', search_results=search_results_html)



if __name__ == "__main__":
    app.run(debug=True)
