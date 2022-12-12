import requests
from flask import Flask, render_template, flash, Markup
import numpy as np
from pandas_datareader import data as wb
import plotly.express as px
import pandas as pd
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, DateField
from wtforms.validators import DataRequired, Length
from flask_bootstrap import Bootstrap
from pandas_datareader._utils import RemoteDataError
from scipy.stats import norm
from datetime import datetime


app = Flask(__name__)
app.config['SECRET_KEY'] = 'jkfafjaewmfdspe032435436964228'
Bootstrap(app)

NEWS_APIKey = "f606545ee6994bdab9db34a8f161a44c"
NEWS_URL = "https://newsapi.org/v2/everything"


NEWS_PARAM = {
    "q" : "AAPL Apple Inc",
    "from" : "2022-11-10",
    "sortBy" : "publishedAt",
    "apiKey" : NEWS_APIKey,
    "Language" : "en"
}

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:66.0) Gecko/20100101 Firefox/66.0",
    "Accept-Encoding": "*",
    "Connection": "keep-alive"
}


class TickerForm(FlaskForm):
    ticker = StringField("Company Ticker", validators=[DataRequired(), Length(min=1, max=5)])
    date_start = DateField('Start Date', format='%Y-%m-%d')
    submit = SubmitField("Get Analysis")


class NewsForm(FlaskForm):
    company = StringField("What Company or Key-word?", validators=[DataRequired()])
    get_news = SubmitField("Get News")


@app.route("/", methods=["GET", "POST"])
def home():
    now = datetime.now()
    now_year = now.year
    news = requests.get(NEWS_URL, NEWS_PARAM, headers=headers)
    news.raise_for_status()
    data_news = news.json()
    # for the jinja
    # for i in range(1, 10):
    #     name = data_news['articles'][i]["source"]["name"]
    #     author = data_news['articles'][i]["author"]
    #     title = data_news['articles'][i]["title"]
    #     description = data_news['articles'][i]["description"]
    #     url = data_news['articles'][i]["url"]
    #     image = data_news['articles'][i]["urlToImage"]
    #     date = data_news['articles'][i]["publishedAt"]
    #     content = data_news['articles'][i]["content"]
    form = NewsForm()
    if form.validate_on_submit():
        try:
            company = form.company.data
            USER_PARAM = {
                "q": company,
                "from": "2022-11-10",
                "sortBy": "publishedAt",
                "apiKey": NEWS_APIKey,
                "Language": "en"
            }
            news = requests.get(NEWS_URL, USER_PARAM, headers=headers)
            news.raise_for_status()
            data = news.json()
            return render_template("index.html", form=form, data=data, now_year=now_year)
        except:
            flash("Could not find the news with that key. Try with another key instead.")
            return render_template("index.html", form=form, data=data_news, now_year=now_year)

    return render_template("index.html", data=data_news, form=form, now_year=now_year)


@app.route("/analysis", methods=["GET", "POST"])
def analysis():
    now = datetime.now()
    now_year = now.year
    form = TickerForm()
    if form.validate_on_submit():
        try:
            ticker = form.ticker.data
            start_date = form.date_start.data
            AAPL = wb.DataReader(str(ticker).upper(), data_source='yahoo', start=f"{start_date}")
            AAPL_head = AAPL.head()
            AAPL_tail = AAPL.tail()
            AAPL['Log Return'] = np.log(AAPL['Adj Close'] / AAPL['Adj Close'].shift(1))
            AAPL_log_return_d = AAPL['Log Return'].mean()
            AAPL_log_return_a = AAPL['Log Return'].mean() * 250
            AAPL_pct = str(round(AAPL_log_return_a, 5) * 100) + ' %'
            daily_risk = AAPL["Log Return"].std()
            annual_risk = AAPL["Log Return"].std() * 250 ** 0.5
            data = pd.DataFrame()
            data[str(ticker).upper()] = wb.DataReader(str(ticker).upper(), data_source='yahoo', start=f"{start_date}")["Adj Close"]
            log_returns = np.log(1 + data.pct_change())
            u = log_returns.mean()
            var = log_returns.var()
            drift = u - (0.5 * var)
            stdev = log_returns.std()
            t_intervals = 250
            iterations = 10
            daily_returns = np.exp(drift.values + stdev.values * norm.ppf(np.random.rand(t_intervals, iterations)))
            S0 = data.iloc[-1]
            price_list = np.zeros_like(daily_returns)
            price_list[0] = S0
            for t in range(1, t_intervals):
                price_list[t] = price_list[t - 1] * daily_returns[t]
            fig = px.line(AAPL['Log Return'])
            div = fig.to_html(full_html=False)
            price_graph = px.line(price_list)
            graph = price_graph.to_html(full_html=False)
            return render_template("about.html", start_date=start_date, form=form, head=[AAPL_head.to_html(classes='data')],
                                   tail=[AAPL_tail.to_html(classes='data')], titles=ticker, daily=AAPL_log_return_d,
                                   annual=AAPL_log_return_a, percent=AAPL_pct, div=Markup(div), daily_risk=daily_risk,
                                   annual_risk=annual_risk, drift=drift, graph=Markup(graph), now_year=now_year)
        except RemoteDataError:
            flash("Sorry, No Data with that ticker. Probably no companies use those characters yet.")
            return render_template("about.html", form=form, now_year=now_year)
    return render_template("about.html", form=form, now_year=now_year)


if __name__ == '__main__':
    app.run(debug=True)