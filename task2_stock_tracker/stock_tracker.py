#ALfarouq Ibrahim _ CodeAlfa _ task 2
stock_prices = {
    "ADOBA ABABA": 1230.0,
    "GOOGO GAGA": 2560.0,
    "AAPLA FAHEATA": 5420.0,
    "TSLA MAN": 930.0,
    "SUEZ STOP": 632.0
}

total_investment = 0.0
user_portfolio = {}

print("Stock Portfolio Tracker")
print("Available stocks:" , list(stock_prices.keys()))
print("-" * 30)

while True:

    stock_name = input("\nEnter Stock Name (or type 'DONE' to finish): ").upper()

    if stock_name == "DONE":
        break

    if stock_name not in stock_prices:
        print("Invalid Stock Name")
        continue

    try:
        quantity = int(input(f"Enter the number of shares for {stock_name}: "))
    except ValueError:
        print("Invalid Stock Name!")
        continue
    price = stock_prices[stock_name]
    total_value = quantity * price

    total_investment += total_value

    user_portfolio[stock_name] = {
        "quantity": quantity,
        "price": price,
        "total_value": total_value
    }

    print (f"Added !{quantity} shares to {stock_name} = ${total_value}")

report_lines = [
    "\n" + "="*30,
    "     PORTFOLIO SUMMARY     ",
    "="*30
]

for stock, data in user_portfolio.items():
    line = f"{stock} | Shares: {data['quantity']} | Value: ${data['total_value']}"
    report_lines.append(line)
    print (line)

report_lines.append("-" * 30)
summary = f"Total Investment: ${total_investment}"
report_lines.append(summary)
print ("-" * 30)
print (summary)
print ("=" * 32)

with open("Portfolio_report.txt", "w") as file:
    for line in report_lines:
        file.write(line + "\n")
print("\nSuccess: A copy of this report has been saved to 'portfolio_report.txt'")