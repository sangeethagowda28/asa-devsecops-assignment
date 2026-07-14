pipeline {

    agent any

    environment {
        IMAGE_NAME = "sangu7991/vulntracker"
        HELM_CHART = "./helm"
        K8S_NAMESPACE = "vulntracker"
        SNYK_TOKEN = credentials('snyk-token')
    }

    stages {

        stage('Checkout') {
            steps {
                checkout scm

                bat '''
                echo Repository checked out successfully
                dir
                '''
            }
        }


        stage('Verify Tools') {
            steps {
                bat '''
                echo Checking installed tools...

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

                echo Tool verification completed
                '''
            }
        }

        stage('Test') {
    steps {
        bat """
        pytest --cov=app --cov-report=xml:reports/coverage.xml
        """
    }
}
        stage('SonarQube Analysis') {
    steps {
        withSonarQubeEnv('SonarQube') {
            withCredentials([string(credentialsId: 'sonar-token', variable: 'SONAR_TOKEN')]) {
                bat """
                sonar-scanner ^
                -Dsonar.token=%SONAR_TOKEN%
                """
            }
        }
    }
}


        stage('Quality Gate') {
            steps {

                timeout(time: 15, unit: 'MINUTES') {

                    waitForQualityGate abortPipeline: true

                }
            }
        }


        stage('Snyk Scan') {
            steps {

                bat '''
                echo Authenticating Snyk...

                snyk auth %SNYK_TOKEN%

                snyk test

                '''
            }
        }


        stage('Docker Build') {
            steps {

                bat '''
                echo Building Docker image...

                docker build ^
                -t %IMAGE_NAME%:%BUILD_NUMBER% ^
                -t %IMAGE_NAME%:latest .

                '''
            }
        }


        stage('Trivy Scan') {
            steps {

                bat '''
                echo Scanning Docker image...

                trivy image ^
                --severity HIGH,CRITICAL ^
                --exit-code 1 ^
                %IMAGE_NAME%:%BUILD_NUMBER%

                '''
            }
        }


        stage('Checkov Scan') {
            steps {

                bat '''
                echo Running Checkov IaC scan...

                checkov -d helm

                '''
            }
        }


        stage('Docker Push') {

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

                    echo %DOCKER_PASS% | docker login ^
                    -u %DOCKER_USER% ^
                    --password-stdin


                    docker push %IMAGE_NAME%:%BUILD_NUMBER%

                    docker push %IMAGE_NAME%:latest


                    docker logout

                    '''
                }
            }
        }


        stage('Helm Lint') {
            steps {

                bat '''

                echo Running Helm lint...

                helm lint %HELM_CHART%

                '''
            }
        }


        stage('Deploy to Kubernetes') {
            steps {

                bat '''

                echo Deploying application...

                helm upgrade --install vulntracker %HELM_CHART% ^
                --namespace %K8S_NAMESPACE% ^
                --create-namespace


                '''
            }
        }


        stage('Verify Deployment') {
            steps {

                bat '''

                echo Checking Kubernetes rollout...


                kubectl rollout status deployment/vulntracker ^
                -n %K8S_NAMESPACE%


                kubectl get all ^
                -n %K8S_NAMESPACE%

                '''
            }
        }

    }


    post {

        success {

            echo '''
            ========================================
            DevSecOps Pipeline Completed Successfully
            ========================================
            '''

        }


        failure {

            echo '''
            ========================================
            Pipeline Failed
            Review Jenkins console logs
            ========================================
            '''

        }


        always {

            cleanWs()

        }
    }
}