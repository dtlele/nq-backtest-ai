import time, subprocess

while True:
    # Run the backtest (you can adjust arguments as needed)
    subprocess.run(["python", "run_backtest.py"], cwd=r"C:/Users/Mauro/Documents/nq-backtest")
    # Wait 5 minutes before next run
    time.sleep(300)
