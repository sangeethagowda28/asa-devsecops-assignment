pipeline {

    agent any

    environment {

        IMAGE_NAME = "sangu7991/vulntracker"
        HELM_CHART = "./helm"
        K8S_NAMESPACE = "vulntracker"

        SNYK_TOKEN = credentials('snyk-token')

        IMAGE_TAG = "${BUILD_NUMBER}"

    }


    stages {


        stage('Checkout') {

            steps {

                checkout scm

                bat '''
                echo Repository checkout completed
                dir
                '''

            }

        }



        stage('Docker Login') {

            steps {

                withCredentials([
                    usernamePassword(
                        credentialsId: 'dockerhub-creds',
                        usernameVariable: 'DOCKER_USER',
                        passwordVariable: 'DOCKER_PASS'
                    )
                ]) {

                    bat '''
                    echo Logging into Docker Hub...
                    setlocal enabledelayedexpansion
                    echo !DOCKER_PASS!| docker login -u !DOCKER_USER! --password-stdin
                    '''

                }

            }

        }



        stage('Verify Tools') {

            steps {

                bat '''

                echo Checking installed tools...


                docker run --rm python:3.12-slim-bookworm python --version
                docker run --rm python:3.12-slim-bookworm pip --version


                where docker
                docker --version


                where kubectl
                kubectl version --client


                docker run --rm alpine/helm version


                where trivy
                trivy --version


                where snyk
                snyk --version


                where sonar-scanner
                sonar-scanner --version


                docker run --rm bridgecrew/checkov --version


                echo Tool verification completed

                '''

            }

        }


        stage('Test') {

            steps {

                bat '''

                echo Running Unit Tests...


                if not exist reports mkdir reports


                docker run --rm ^
                  -v "%WORKSPACE%:/workspace" ^
                  -w /workspace ^
                  python:3.12-slim-bookworm ^
                  sh -c "pip install -r requirements.txt && pytest --cov=app --cov-report=xml:reports/coverage.xml"


                '''

            }

        }






        stage('SonarQube Analysis') {

            steps {

                withSonarQubeEnv('sonarqube') {


                    withCredentials([
                        string(
                            credentialsId: 'sonar-token',
                            variable: 'SONAR_TOKEN'
                        )
                    ]) {


                        bat '''

                        echo Running SonarQube Scan...


                        sonar-scanner ^
                        -Dsonar.token=%SONAR_TOKEN%


                        '''

                    }

                }

            }

        }






        stage('Quality Gate') {

            steps {


                timeout(
                    time:15,
                    unit:'MINUTES'
                ) {


                    waitForQualityGate(
                        abortPipeline:true
                    )


                }

            }

        }







        stage('Snyk Scan') {


            steps {


                bat '''

                echo Running Snyk Security Scan...


                docker run --rm ^
                  --entrypoint "" ^
                  -v "%WORKSPACE%:/app" ^
                  -w /app ^
                  -e SNYK_TOKEN=%SNYK_TOKEN% ^
                  snyk/snyk:python ^
                  sh -c "pip install -r requirements.txt && snyk test --file=requirements.txt --package-manager=pip --severity-threshold=high --fail-on=upgradable"

                '''

            }

        }







        stage('Docker Build') {


            steps {


                bat '''

                echo Building Docker Image...


                docker build --no-cache ^
                -t %IMAGE_NAME%:%IMAGE_TAG% ^
                -t %IMAGE_NAME%:latest .


                '''

            }

        }







        stage('Trivy Scan') {


            steps {


                bat '''

                echo Running Trivy Scan...


                trivy image ^
                --severity HIGH,CRITICAL ^
                --ignore-unfixed ^
                --exit-code 1 ^
                %IMAGE_NAME%:%IMAGE_TAG%


                '''

            }

        }







        stage('Checkov Scan') {


            steps {


                bat '''

                echo Running Checkov Scan...


                docker run --rm -v "%WORKSPACE%:/work" -w /work bridgecrew/checkov -d helm


                '''

            }

        }







        stage('Docker Push') {


            steps {


                bat '''

                echo Pushing Docker Image...


                docker push %IMAGE_NAME%:%IMAGE_TAG%


                docker push %IMAGE_NAME%:latest


                '''

            }

        }







        stage('Helm Lint') {


            steps {


                bat '''

                echo Helm validation...


                docker run --rm -v "%WORKSPACE%:/apps" alpine/helm lint /apps/helm


                '''

            }

        }








        stage('Deploy Kubernetes') {


            steps {


                bat '''


                echo Deploying application...


                docker run --rm ^
                  -v "%WORKSPACE%:/apps" ^
                  -v "%USERPROFILE%\\.kube:/root/.kube" ^
                  alpine/helm upgrade --install vulntracker /apps/helm ^
                  --namespace %K8S_NAMESPACE% ^
                  --create-namespace ^
                  --set image.repository=%IMAGE_NAME% ^
                  --set image.tag=%IMAGE_TAG%



                '''

            }

        }







        stage('Verify Deployment') {


            steps {


                bat '''


                echo Checking deployment...


                kubectl rollout status deployment/vulntracker ^
                -n %K8S_NAMESPACE%



                kubectl get pods ^
                -n %K8S_NAMESPACE%



                kubectl get svc ^
                -n %K8S_NAMESPACE%



                '''

            }

        }



    }




    post {


        success {


            echo '''

            =========================================
            DevSecOps Pipeline Completed Successfully
            =========================================

            '''

        }



        failure {


            echo '''

            =========================================
            Pipeline Failed
            Check Jenkins Logs
            =========================================

            '''

        }



        always {


            bat 'docker logout'


            cleanWs()

        }


    }


}