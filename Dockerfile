FROM ubuntu:22.04

RUN apt-get update && apt-get install -y openssh-server && \
    mkdir /var/run/sshd && \
    useradd -m -s /bin/bash agro && \
    echo "agro:frol261262" | chpasswd && \
    mkdir -p /home/agro/upload && \
    chown agro:agro /home/agro/upload && \
    echo "PasswordAuthentication yes" >> /etc/ssh/sshd_config && \
    echo "ChallengeResponseAuthentication no" >> /etc/ssh/sshd_config && \
    echo "PermitRootLogin no" >> /etc/ssh/sshd_config

EXPOSE 22

CMD ["/usr/sbin/sshd", "-D"]
