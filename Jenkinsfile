parallel (

	"docker":{	
	node('DOCKER') {

		stage('build-docker-image') {
			gitlabCommitStatus("build-docker-image") {
				if (env.BRANCH_NAME == 'master') {
					checkout scm				
					sh "make docker-build"
				} else {
					echo "Nothing to do, because branch is not master"
				}
			}
		}

		stage('test-docker-images') {
			gitlabCommitStatus("test-docker-images") {
				if (env.BRANCH_NAME == 'master') {
					sh "./script/test/test_docker_output.sh"
				} else {
					echo "Nothing to do, because branch is not master"
				}
			}
		}

        stage('deploy-docker-image') {
			gitlabCommitStatus("build-docker-image") {

				if (env.BRANCH_NAME == 'master') {
					withCredentials([string(credentialsId: 'svc_lidarhd', variable: 'svc_lidarhd')]) {
						sh "docker/deploy-jenkins.sh ${svc_lidarhd}"
					}
				} else {
					echo "Nothing to do, because branch is not master"
				}

			}
		}

	}
	}
)