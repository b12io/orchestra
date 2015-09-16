from orchestra.models import WorkerCertification


def worker_has_certificate(worker,
                           certification,
                           role):
    return (WorkerCertification.objects
            .filter(worker=worker,
                    certification=certification,
                    role=role)
            .exists())


def is_reviewer(worker, certification):
    return worker_has_certificate(worker,
                                  certification,
                                  WorkerCertification.Role.REVIEWER)


def is_entry_level(worker, certification):
    return worker_has_certificate(worker,
                                  certification,
                                  WorkerCertification.Role.ENTRY_LEVEL)
