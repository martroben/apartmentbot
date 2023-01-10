FROM python:3.10
ADD data_processor_requirements.txt entrypoint.sh /
RUN pip install -r data_processor_requirements.txt
ENTRYPOINT ["/entrypoint.sh"]
