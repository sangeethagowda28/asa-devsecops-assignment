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



        stage('Verify Tools') {

            steps {

                bat '''

                echo Checking installed tools...


                where python
                python --version


                where pip
                pip --version


                where docker
                docker --version


                where kubectl
                kubectl version --client


                where helm
                helm version


                where trivy
                trivy --version


                where snyk
                snyk --version


                where sonar-scanner
                sonar-scanner --version


                where checkov
                checkov --version


                echo Tool verification completed

                '''

            }

        }




        stage('Install Dependencies') {

            steps {

                bat '''

                echo Installing Python dependencies...

                python --version

                python -m pip --version

                python -m pip install --upgrade pip

                python -m pip install -r requirements.txt


                '''

            }

        }





        stage('Test') {

            steps {

                bat '''

                echo Running Unit Tests...


                if not exist reports mkdir reports


                pytest ^
                --cov=app ^
                --cov-report=xml:reports/coverage.xml


                '''

            }

        }






        stage('SonarQube Analysis') {

            steps {


                withSonarQubeEnv('SonarQube') {


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


                set SNYK_TOKEN=%SNYK_TOKEN%


                snyk test ^
                --severity-threshold=high


                '''

            }

        }







        stage('Docker Build') {


            steps {


                bat '''

                echo Building Docker Image...


                docker build ^
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
                --exit-code 1 ^
                %IMAGE_NAME%:%IMAGE_TAG%


                '''

            }

        }







        stage('Checkov Scan') {


            steps {


                bat '''

                echo Running Checkov Scan...


                checkov -d helm


                '''

            }

        }







        stage('Docker Push') {


            steps {


                withCredentials([

                    usernamePassword(

                        credentialsId:'dockerhub-creds',

                        usernameVariable:'DOCKER_USER',

                        passwordVariable:'DOCKER_PASS'

                    )

                ]) {



                    bat '''

                    echo Logging into Docker Hub...


                    echo %DOCKER_PASS% | docker login ^
                    -u %DOCKER_USER% ^
                    --password-stdin



                    docker push %IMAGE_NAME%:%IMAGE_TAG%


                    docker push %IMAGE_NAME%:latest



                    docker logout


                    '''

                }


            }

        }







        stage('Helm Lint') {


            steps {


                bat '''

                echo Helm validation...


                helm lint %HELM_CHART%


                '''

            }

        }








        stage('Deploy Kubernetes') {


            steps {


                bat '''


                echo Deploying application...


                helm upgrade --install vulntracker %HELM_CHART% ^
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


            cleanWs()

        }


    }


}