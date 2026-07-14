pipeline {

    agent any

    environment {
        IMAGE_NAME = "sangu7991/vulntracker"
        HELM_CHART = "./helm"
        K8S_NAMESPACE = "vulntracker"
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

       stage('SonarQube Scan') {
    steps {
        script {
            def scannerHome = tool 'sonar-scanner'

            withSonarQubeEnv('sonarqube') {
                bat """
                ${scannerHome}\\bin\\sonar-scanner.bat
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
        withCredentials([
            string(credentialsId: 'snyk-token', variable: 'SNYK_TOKEN')
        ]) {
            bat '''
            snyk auth %SNYK_TOKEN%
            snyk test
            '''
        }
    }
}

        stage('Docker Build') {
            steps {
                bat '''
                    docker build \
                      -t $IMAGE_NAME:$BUILD_NUMBER \
                      -t $IMAGE_NAME:latest .
                '''
            }
        }

        stage('Trivy Scan') {
            steps {
                bat '''
                    trivy image \
                      --severity HIGH,CRITICAL \
                      --exit-code 1 \
                      $IMAGE_NAME:$BUILD_NUMBER
                '''
            }
        }

        stage('Checkov Scan') {
            steps {
                bat '''
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
                        echo $DOCKER_PASS | docker login \
                          -u $DOCKER_USER \
                          --password-stdin

                        docker push $IMAGE_NAME:$BUILD_NUMBER
                        docker push $IMAGE_NAME:latest

                        docker logout
                    '''
                }
            }
        }

        stage('Helm Lint') {
            steps {
                bat '''
                    helm lint $HELM_CHART
                '''
            }
        }

        stage('Deploy to Kubernetes') {
            steps {
                bat '''
                    helm upgrade --install vulntracker $HELM_CHART \
                      --namespace $K8S_NAMESPACE \
                      --create-namespace
                '''
            }
        }

        stage('Verify Deployment') {
            steps {
                bat '''
                    kubectl rollout status deployment/vulntracker \
                      -n $K8S_NAMESPACE

                    kubectl get all \
                      -n $K8S_NAMESPACE
                '''
            }
        }
        stage('Verify Tools') {
    steps {
        bat '''
        where.exe sonar-scanner
        sonar-scanner --version
        '''
    }
}
    }

    post {

        success {
            echo '========================================'
            echo 'DevSecOps Pipeline Completed Successfully'
            echo '========================================'
        }

        failure {
            echo '========================================'
            echo 'Pipeline Failed'
            echo 'Review Jenkins console logs.'
            echo '========================================'
        }

        always {
            cleanWs()
        }
    }
}