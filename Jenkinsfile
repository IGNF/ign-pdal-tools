parallel (

	"docker":{	
	node('DOCKER') {

		stage('build-docker-image') {
			gitlabCommitStatus("build-docker-image") {
				checkout scm				
				sh "make docker-build"
			}
		}

        stage('deploy-docker-image') {
			gitlabCommitStatus("build-docker-image") {
                withCredentials([string(credentialsId: 'svc_lidarhd', variable: 'svc_lidarhd')]) {
				    sh "docker/deploy-jenkins.sh ${svc_lidarhd}"
                }
			}
		}

	}
	}
)