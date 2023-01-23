FROM python:3.10
ADD reporter_requirements.txt reporter_entrypoint.sh /
RUN chmod +x /reporter_entrypoint.sh
RUN pip install -r reporter_requirements.txt
ENTRYPOINT ["/reporter_entrypoint.sh"]
