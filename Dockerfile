FROM python:3.9-slim-buster

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY match_list_processor.py .
COPY create_group_description.py .

CMD ["python", "match_list_processor.py"]