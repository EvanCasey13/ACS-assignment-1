#!/usr/bin/env python3

import boto3
import json
import webbrowser
import random
from botocore.exceptions import ClientError
from subprocess import run
import sys
ec2 = boto3.resource('ec2')
client = boto3.client('ec2')
Vpc_Id= 'vpc-04d617b4f88cb3b0b'

# Configure security group #

group_name = input("Enter security group name: ")
print('Group name is: ' + group_name)

try:
    security_group = ec2.create_security_group(
	Description='Assignment 1 Inbound',
	GroupName=group_name,
	VpcId=Vpc_Id,
	TagSpecifications=[
	    {
		'ResourceType': 'security-group',
		'Tags': [
		    {
			'Key': 'assignment_1',
			'Value': 'allow-inbound-ssh'
		    },
		]
	    },
	],
)

except ClientError as e:
        if e.response['Error']['Code'] == 'InvalidGroup.Duplicate':
                print(e.response['Error']['Message'])
        else:
                print('Unexpected error: %s ' % e)

# Inbound rules #

security_group.authorize_ingress(
	CidrIp='0.0.0.0/0',
	FromPort=80,
	ToPort=80,
	IpProtocol='tcp'
)

security_group.authorize_ingress(
	CidrIp='0.0.0.0/0',
	FromPort=22,
	ToPort=22,
	IpProtocol='tcp'
)

security_group.authorize_ingress(
        CidrIp='0.0.0.0/0',
        FromPort=443,
        ToPort=443,
        IpProtocol='tcp'
)

# Create Key pair #

key_name = input("Enter a name for your Key Pair: ")
print('Key Pair name is: ' + key_name)

key_pair = ec2.create_key_pair(
	KeyName=key_name,
	DryRun=False,
	KeyType='rsa',
	TagSpecifications=[
		{
		    'ResourceType': 'key-pair',
		    'Tags': [
			{
			    'Key': 'assignment_1',
			    'Value': 'assignment_1_key_pair'
			},
		   ]
	      },
	]
)

# Save key pair #

with open(key_name + '.pem', 'w') as file:
	file.write(key_pair.key_material)

cmd_permissions = 'chmod 400 ' + key_name + '.pem'
run(cmd_permissions.split())

# User data script #

Userdata_script = '''
#!/bin/bash
yum update -y
yum install httpd -y
systemctl start httpd
systemctl enable httpd

echo "<h2>Assignment One</h2>Instance ID: " > /var/www/html/index.html
curl --silent http://169.254.169.254/latest/meta-data/instance-id/ >> /var/www/html/index.html
echo "<br>Availability zone: " >> /var/www/html/index.html
curl --silent http://169.254.169.254/latest/meta-data/placement/availability-zone/ >> /var/www/html/index.html
echo "<br>IP address: " >> /var/www/html/index.html
curl --silent http://169.254.169.254/latest/meta-data/local-ipv4 >> /var/www/html/index.html
'''

# Tag Specifications #

tag_name = input("Enter a name for your tag: ")

instance_tag = [
        {
        "ResourceType":"instance",
        "Tags": [
                {
                    "Key": tag_name,
                    "Value": "Assignment 1 ACS - EC 2022"
                }
            ]
    }
    ]

# Start Instance #

instance = ec2.create_instances(
        ImageId='ami-0bf84c42e04519c85',
        MinCount=1,
        MaxCount=1,
        InstanceType='t2.nano',
	UserData=Userdata_script,
	KeyName=key_pair.name,
	TagSpecifications = instance_tag,
	SecurityGroupIds=[security_group.group_id]
)

print('New EC2 Instance created: ' + instance[0].id)

# Open EC2 Website #
instance[0].wait_until_running()

print('Instance running')

instance[0].reload()

public_ip = instance[0].public_ip_address

webbrowser.get("firefox").open('http://' + str(public_ip))

# Secure copy Monitor.sh file to new EC2 Instance #
try:
	cmd = 'scp -i ' + key_name + '.pem monitor.sh ec2-user@' + public_ip + ':.'
	run(cmd.split())

except ClientError as e:
	print(e.response['Error']['Message'])

# Script permissions #
try:
	cmd_monitor_perms = 'ssh -i' + key_name + '.pem ec2-user@' + public_ip + ' chmod 700 monitor.sh'
	run(cmd_monitor_perms.split())

except ClientError as e:
	print(e.response['Error']['Message'])

# SSH remote command execution #
try:
	cmd_execute_monitor = 'ssh -i' + key_name + '.pem ec2-user@' + public_ip + ' bash monitor.sh'
	run(cmd_execute_monitor.split())

except ClientError as e:
	print(e.response['Error']['Message'])

# S3 Website #

# Create bucket #

bucket_name = input('Enter a name for your bucket: ')
print('Bucket name is: ' + bucket_name)

region='eu-west-1'
try:
	    s3 = boto3.resource('s3', region_name=region)
	    location = {'LocationConstraint': region}
	    s3.create_bucket(Bucket=bucket_name,
				    CreateBucketConfiguration=location)
except ClientError as e:
    print(e.response['Error']['Message'])

# Set Bucket policy #

s3_client = boto3.client('s3')

bucket_policy = {
	'Version': '2012-10-17',
	'Statement': [{
	     'Sid': 'AddPerm',
 	     'Effect': 'Allow',
	     'Principal': '*',
	     'Action': ['s3:GetObject'],
	     'Resource': 'arn:aws:s3:::%s/*' % bucket_name
	}]
  }

bucket_policy = json.dumps(bucket_policy)

s3_client.put_bucket_policy(Bucket=bucket_name, Policy=bucket_policy)

# Download Image #

download_bucket='witacsresources'
Image='image.jpg'

try:
	download = s3.Bucket(download_bucket).download_file(Image, 'my_local_image.jpg')
except ClientError as e:
	if e.response['Error']['Code'] == "404":
	     print('The object does not exist.')
	else:
	    raise

# Add to my bucket #

s3.Bucket(bucket_name).upload_file('my_local_image.jpg', 'uploaded_image.jpg')

# Enabling Static Website Hosting on bucket #

# Generating presigned url #

try:
	response_img_url = s3_client.generate_presigned_url('get_object',
						    Params={'Bucket': bucket_name,
                    				            'Key': 'uploaded_image.jpg'})
except ClientError as e:
	print(e)

text ='''
<html>
  <body>
        <br> Here is the image stored on the S3 bucket: </br>
	<img src="uploaded_image.jpg"/>
  </body>
</html>
'''

file = open("index.html", "w")
file.write(text)
file.close()

error_text = '''
<html>
 <body>
	<h1> Error loading static website </h1>
 </body>
</html>
'''

# S3 Bucket Static website configuration #

website_configuration = {
	'ErrorDocument': {'Key': 'error.html'},
	'IndexDocument': {'Suffix': 'index.html'},
}

bucket_website = s3.BucketWebsite(bucket_name)

bucket_website.put(WebsiteConfiguration=website_configuration)

s3.Object(bucket_name, 'index.html').put(Body=text, ContentType='text/html')
s3.Object(bucket_name, 'error.html').put(Body=text, ContentType='text/html')

webbrowser.get("firefox").open('http://' + bucket_name + '.s3-website-eu-west-1.amazonaws.com')

# List Instances #
def list_instances():
	for instance in ec2.instances.all():
         print (instance.id, instance.state)

# Run Monitor #
def run_monitor():
	cmd_execute_monitor = 'ssh -i' + key_name + '.pem ec2-user@' + public_ip + ' bash monitor.sh'
	run(cmd_execute_monitor.split())

if __name__ == "__main__":
    list_instances()
    run_monitor()

# CloudWatch Metrics #

cloud_client = boto3.client('cloudwatch', region_name='eu-west-1')

for i in range(10):
    cloud_response = cloud_client.put_metric_data(
        Namespace='Web Metric',
        MetricData=[
            {
                'MetricName': 'Number of visits',
                'Dimensions': [
                    {
                        'Name': 'Device',
                        'Value': 'Ubuntu'
                    }, {
                        'Name': 'page',
                        'Value': 'index.html'
                    }
                ],
                'Value': random.randint(1, 5),
                'Unit': 'Count'
            },
        ]
    )

    print(json.dumps(cloud_response, indent=4))
