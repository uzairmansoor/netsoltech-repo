import boto3
import os
import json
from datetime import date, datetime, timedelta

ec2 = boto3.client('ec2')
ssm = boto3.client('ssm')


def lambda_handler(event, context):

    json.dumps(event)
    image_id = event['ImageId']
    amiIdParamStoreName = os.environ.get("amiIdParamStoreName")
    ami_name = get_ami_name(image_id)
    put_ssm_parameter(amiIdParamStoreName,image_id)
    if os.environ.get("project") in ami_name and os.environ.get("env") in ami_name:
        latest_launch_template_version = get_latest_launch_template_version()
        if latest_launch_template_version:
            update_asg_launch_template(image_id,latest_launch_template_version)
    
    return {
        'statusCode': 200,
        'body': 'Successfully updated ASG Launch Template'
    }


def get_ami_name(image_id):
    response = ec2.describe_images(
        Filters = [
            {
                'Name': 'image-id',
                'Values': [image_id]
            }
        ]
    )
    if 'Images' in response:
        images = response['Images']
        if images:
            image = images[0]
            for tag in image.get('Tags', []):
                if tag['Key'] == 'Name':
                    return tag['Value']
  
def put_ssm_parameter(param_name,value):
    response = ssm.put_parameter(
        Name = param_name,
        Type = 'String',
        Value = value,
        Overwrite = True
    )


def get_latest_launch_template_version():
    response = ec2.describe_launch_template_versions(
        LaunchTemplateName = os.environ.get("launchTemplateName")
    )
    sorted_versions = sorted(response['LaunchTemplateVersions'], key=lambda x: int(x['VersionNumber']), reverse=True)
    if sorted_versions:
        return sorted_versions[0]
    return None


def update_asg_launch_template(image_id,latest_launch_template_version):
    response = ec2.create_launch_template_version(
        LaunchTemplateName = latest_launch_template_version['LaunchTemplateName'],
        LaunchTemplateData = {
            'IamInstanceProfile': {
                'Name': latest_launch_template_version['LaunchTemplateData']['IamInstanceProfile']['Name']
            },
            'ImageId': image_id,
            'InstanceType': latest_launch_template_version['LaunchTemplateData']['InstanceType'],
            'Monitoring': {
                'Enabled': latest_launch_template_version['LaunchTemplateData']['Monitoring']['Enabled']
            },
            'TagSpecifications': [
                {
                    'ResourceType': latest_launch_template_version['LaunchTemplateData']['TagSpecifications'][0]['ResourceType'],
                    'Tags': [
                        {
                            'Key': 'Name',
                            'Value': os.environ.get("project") + "-" + os.environ.get("env") + "-" + "ec2Instance" + "-" + os.environ.get('AWS_REGION')
                            # 'Value': os.environ.get("project") + "-" + os.environ.get("env") + "launchTemplateVersionNo." + "-" + str(latest_launch_template_version['VersionNumber']) + "-" + os.environ.get('AWS_REGION') 
                        },
                         {
                            'Key': 'project',
                            'Value': os.environ.get("project")
                        },
                         {
                            'Key': 'environment',
                            'Value': os.environ.get("env")
                        }]}],
                'BlockDeviceMappings': [
                    {
                        'DeviceName': latest_launch_template_version['LaunchTemplateData']['BlockDeviceMappings'][0]['DeviceName'],
                        'Ebs': {
                            'VolumeSize': latest_launch_template_version['LaunchTemplateData']['BlockDeviceMappings'][0]['Ebs']['VolumeSize'],
                            'VolumeType': latest_launch_template_version['LaunchTemplateData']['BlockDeviceMappings'][0]['Ebs']['VolumeType']
                        }
                        
                    }],
                    'KeyName': latest_launch_template_version['LaunchTemplateData']['KeyName'],
                    'SecurityGroupIds': latest_launch_template_version['LaunchTemplateData']['SecurityGroupIds']
                    })