#!/bin/bash
# Increase file descriptor limit
sudo sysctl -w fs.file-max=100000

# Install Java
sudo apt-get update
sudo apt-get install -y openjdk-11-jre

# Download and Extract Confluent Community Edition
wget https://packages.confluent.io/archive/7.5/confluent-community-7.5.0.tar.gz
tar -xzf confluent-community-7.5.0.tar.gz
sudo mv confluent-7.5.0 /opt/confluent

# Create a systemd service for Zookeeper
cat <<EOT | sudo tee /etc/systemd/system/zookeeper.service
[Unit]
Description=Apache Zookeeper server
Requires=network.target remote-fs.target
After=network.target remote-fs.target

[Service]
Type=simple
User=root
ExecStart=/opt/confluent/bin/zookeeper-server-start /opt/confluent/etc/kafka/zookeeper.properties
ExecStop=/opt/confluent/bin/zookeeper-server-stop
Restart=on-abnormal

[Install]
WantedBy=multi-user.target
EOT

# Create a systemd service for Kafka
cat <<EOT | sudo tee /etc/systemd/system/kafka.service
[Unit]
Description=Apache Kafka Server
Requires=zookeeper.service
After=zookeeper.service

[Service]
Type=simple
User=root
ExecStart=/opt/confluent/bin/kafka-server-start /opt/confluent/etc/kafka/server.properties
ExecStop=/opt/confluent/bin/kafka-server-stop
Restart=on-abnormal

[Install]
WantedBy=multi-user.target
EOT

# Create a systemd service for Schema Registry
cat <<EOT | sudo tee /etc/systemd/system/schema-registry.service
[Unit]
Description=Confluent Schema Registry
Requires=kafka.service
After=kafka.service

[Service]
Type=simple
User=root
ExecStart=/opt/confluent/bin/schema-registry-start /opt/confluent/etc/schema-registry/schema-registry.properties
ExecStop=/opt/confluent/bin/schema-registry-stop
Restart=on-abnormal

[Install]
WantedBy=multi-user.target
EOT

# Start the services
sudo systemctl start zookeeper
sudo systemctl start kafka
sudo systemctl start schema-registry

# Enable them to start on boot
sudo systemctl enable zookeeper
sudo systemctl enable kafka
sudo systemctl enable schema-registry