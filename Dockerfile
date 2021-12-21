# ===============
# --- Release ---
# ===============
FROM python:3.7.9-buster
LABEL maintainer="data_visualization"

ENV http_proxy "http://100.98.146.3:8080"
ENV https_proxy "http://100.98.146.3:8080"
ENV ftp_proxy "http://100.98.146.3:8080"
ENV env "product"

RUN mkdir -p /data_visualization

WORKDIR /data_visualization
COPY ./ ./
RUN pip3 install -r requirements.txt

EXPOSE 8000

CMD ["python3", "manage.py", "runserver", "0.0.0.0:8000"]
