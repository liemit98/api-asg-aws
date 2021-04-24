#!flask/bin/python
from flask import Flask, jsonify
from datetime import date
import boto3
import json

client = boto3.client('autoscaling')
client_ec2 = boto3.client('ec2')
ec2 = boto3.resource('ec2')

app = Flask(__name__)
#------ Time ------
today = date.today()
fdate = today.strftime("%d/%m/%Y")
#------ Time ------
output = {
    "result" : "false",
    "LC" : "abc"
}

@app.route('/asg/<string:asg_name>/<string:ami_new>', methods=['GET'])
def update_asg(asg_name, ami_new):
    output['LC'] = asg_name
    
    # get info target ASG:
    response = client.describe_auto_scaling_groups(AutoScalingGroupNames=[asg_name])  
    if not response['AutoScalingGroups']:
        return 'No such ASG'

    # get InstanceID of target ASG:
    ins_id = response['AutoScalingGroups'][0]['Instances'][0]['InstanceId']
    # get new Ami
    newAMI = ami_new
    print('Image_id created : ' + newAMI)

    # get the snapshotID of the source AMI
    responseAmi = client_ec2.describe_images(ImageIds=[newAMI])
    sourceAmiSnapshot = responseAmi.get('Images')[0]['BlockDeviceMappings'][0]['Ebs']['SnapshotId']
    print('New source AMI: ' + newAMI + " has snapshot ID: " + sourceAmiSnapshot)

    # get block devices
    sourceLaunchConfig = response.get('AutoScalingGroups')[0]['LaunchConfigurationName']
    print('current launch config name:' + sourceLaunchConfig)
    responseLC = client.describe_launch_configurations(LaunchConfigurationNames=[sourceLaunchConfig])
    sourceBlockDevices = responseLC.get('LaunchConfigurations')[0]['BlockDeviceMappings']
    print('Current LC block devices:')
    print(sourceBlockDevices[0]['Ebs'])
    sourceBlockDevices[0]['Ebs']['SnapshotId'] = sourceAmiSnapshot
    print('New LC block devices (snapshotID changed):')
    print(sourceBlockDevices[0]['Ebs'])

    # create LC using instance from target ASG
    newLaunchConfigName = asg_name + fdate
    print('new launch config name: ' + newLaunchConfigName)
    respone_newLC = client.create_launch_configuration(
        InstanceId = ins_id,
        LaunchConfigurationName=newLaunchConfigName,
        ImageId= newAMI,
        BlockDeviceMappings = sourceBlockDevices )

    if respone_newLC['ResponseMetadata']['HTTPStatusCode'] == 200:
        # update ASG to use new LC
        response_final = client.update_auto_scaling_group(AutoScalingGroupName = asg_name,LaunchConfigurationName = newLaunchConfigName)
        output['result'] = 'true'
        print(response_final)

    return jsonify(output)


@app.route('/create/<string:asg_name>', methods=['GET'])
def create_ami(asg_name):

    response = client.describe_auto_scaling_groups(AutoScalingGroupNames=[asg_name])  
    if not response['AutoScalingGroups']:
        return 'No such ASG'

    # Lay InstanceID hien tai cua ASG:
    ins_id = response['AutoScalingGroups'][0]['Instances'][0]['InstanceId']
    
    name_ins = asg_name +'-'+ fdate
    ins_new = client_ec2.create_image(
        Description=name_ins,
        InstanceId=ins_id,
        Name=name_ins,
        NoReboot=True
    )
    newAMI = ins_new['ImageId']
    print('Image_id created : ' + newAMI)
    if ins_new['ResponseMetadata']['HTTPStatusCode'] == 200:
        return jsonify({"result" : "true", "newAMI": newAMI})
    else:
        return jsonify({"result" : "false"})

@app.route('/roll/<string:asg_name>', methods=['GET'])
def rolling_asg(asg_name):

    # Rolling update new ima
    response = client.start_instance_refresh(
        AutoScalingGroupName=asg_name,
        Strategy='Rolling',
    )
    print(response)
    if response['ResponseMetadata']['HTTPStatusCode'] == 200:
        return jsonify({"result" : "true"})
    else:
        return jsonify({"result" : "false"})

if __name__ == '__main__':
    app.run(debug=False)