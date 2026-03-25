FROM atmoz/sftp:debian

RUN sed -i 's/PasswordAuthentication no/PasswordAuthentication yes/' /etc/ssh/sshd_config || true
RUN echo "PasswordAuthentication yes" >> /etc/ssh/sshd_config
RUN echo "AuthenticationMethods password" >> /etc/ssh/sshd_config
