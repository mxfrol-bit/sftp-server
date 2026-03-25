FROM atmoz/sftp:debian

COPY sshd_custom.conf /etc/ssh/sshd_config.d/custom.conf

RUN mkdir -p /etc/sftp.d && \
    printf '#!/bin/bash\ncat /etc/ssh/sshd_config.d/custom.conf >> /etc/ssh/sshd_config\nsed -i "s/PasswordAuthentication no/PasswordAuthentication yes/g" /etc/ssh/sshd_config\nsed -i "/AuthenticationMethods publickey/d" /etc/ssh/sshd_config\n' > /etc/sftp.d/enable-password.sh && \
    chmod +x /etc/sftp.d/enable-password.sh
