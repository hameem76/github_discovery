from diagrams import Diagram, Cluster
from diagrams.aws.compute import EC2Instances, EC2Ami, LambdaFunction, EC2Instance, EC2
from diagrams.aws.database import RDS
from diagrams.aws.network import ELB

# with Diagram("Diagram", direction="TB"):
#     with Cluster("Compute Cluster"):
#         EC2 = EC2("EC2")
#         EC2Instance = EC2Instance("EC2Instance")
#         EC2Instances = EC2Instances("EC2Instances")
#         EC2Ami = EC2Ami("EC2Ami")
#         LambdaFunction = LambdaFunction("LambdaFunction")
#
#         EC2 >> EC2Instance >> LambdaFunction


def generate_architecture_diagram():
    from diagrams.aws.compute import EC2Instances, EC2Ami, LambdaFunction, EC2Instance, EC2

    with Diagram("Diagram", direction="TB", filename="/tmp/diagram"):
        with Cluster("Compute Cluster"):
            EC2=EC2("EC2")
            EC2Instance=EC2Instance("EC2Instance")
            EC2Instances=EC2Instances("EC2Instances")
            EC2Ami=EC2Ami("EC2Ami")
            LambdaFunction=LambdaFunction("LambdaFunction")

            EC2 >> EC2Instance >> LambdaFunction

if __name__ == '__main__':
    generate_architecture_diagram()