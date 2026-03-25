FROM atmoz/sftp:debian

RUN mkdir -p /etc/sftp.d

RUN printf '#!/bin/bash\nsed -i "s/PasswordAuthentication no/PasswordAuthentication yes/g" /etc/ssh/sshd_config\nsed -i "/AuthenticationMethods/d" /etc/ssh/sshd_config\necho "PasswordAuthentication yes" >> /etc/ssh/sshd_config\n' > /etc/sftp.d/enable-password.sh && chmod +x /etc/sftp.d/enable-password.sh
