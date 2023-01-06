FROM python:3.10
ADD c24_requirements.txt chrome_install.sh entrypoint.sh /
RUN chmod +x /chrome_install.sh
RUN chmod +x /entrypoint.sh
RUN /chrome_install.sh 107
RUN pip install -r c24_requirements.txt
RUN apt install xvfb -y
ENTRYPOINT ["/entrypoint.sh"]
