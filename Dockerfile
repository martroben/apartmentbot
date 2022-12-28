FROM python:3.10
ADD requirements.txt chrome_install.sh entrypoint.sh /
ENV DISPLAY=:1
RUN chmod +x /chrome_install.sh
RUN chmod +x /entrypoint.sh
RUN sh -c "/chrome_install.sh"
RUN pip install -r requirements.txt
RUN apt install xvfb -y
ENTRYPOINT ["/entrypoint.sh"]
CMD bash
