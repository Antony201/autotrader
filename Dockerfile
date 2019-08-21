FROM python:3.7.0
WORKDIR /code
COPY ./requirements.txt /tmp
RUN pip install --no-cache-dir -r /tmp/requirements.txt
CMD ["python", "checker.py"]