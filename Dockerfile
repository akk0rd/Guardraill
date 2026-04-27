FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download spaCy language models
RUN python -m spacy download uk_core_news_sm
RUN python -m spacy download en_core_web_sm
RUN python -m spacy download ru_core_news_sm

COPY . .

RUN chmod +x start.sh

# Analyzer on 5002, Anonymizer on 5001
EXPOSE 5001 5002

CMD ["./start.sh"]
