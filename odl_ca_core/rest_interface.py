'''
Created on Oct 1, 2014

@author: fabiomignini
@author: giacomoratta
'''

import logging, json, jsonschema, requests, falcon
from falcon.http_error import HTTPError as falconHTTPError
import falcon.status_codes  as falconStatusCodes
from sqlalchemy.orm.exc import NoResultFound

# Orchestrator Core
from odl_ca_core.user_authentication import UserAuthentication
from odl_ca_core.opendaylight_ca import OpenDayLightCA

# NF-FG
from nffg_library.validator import ValidateNF_FG
from nffg_library.nffg import NF_FG
from nffg_library.exception import NF_FGValidationError

# Exceptions
from odl_ca_core.exception import wrongRequest, unauthorizedRequest, sessionNotFound, NffgUselessInformations,\
    UserNotFound, TenantNotFound



class OpenDayLightCA_REST_Base(object):
    '''
    All the classess "OpenDayLightCA_REST_*" must inherit this class.
    This class contains:
        - common json response creator "_json_response"
        - common exception handlers "__except_*"
    '''
    
    def _json_response(self, http_status, message=None, status=None, nffg=None, userdata=None):
        response_json = {}
        response_json['http_status'] = http_status
        
        if message is not None:
            response_json['message'] = message
        if status is not None:
            response_json['status'] = status
        if nffg is not None:
            response_json['nf-fg'] = nffg
        if userdata is not None:
            response_json['user-data'] = userdata

        return json.dumps(response_json)
        
    
    '''
    Section: "Common Exception Handlers"
    '''
    
    def __get_exception_message(self,ex):
        if hasattr(ex, "arg") and ex.arg[0] is not None:
            return ex.arg[0]
        elif hasattr(ex, "message") and ex.message is not None:
            return ex.message
        else:
            return "Unknown exception message"
        
    
    def _except_BadRequest(self, prefix, ex):
        message = self.__get_exception_message(ex)
        logging.error(prefix+": "+message)
        #raise falcon.HTTPBadRequest('Bad Request',message)
        raise falconHTTPError(falconStatusCodes.HTTP_400,'Bad Request',message)
    
    def _except_NotAcceptable(self, prefix, ex):
        message = self.__get_exception_message(ex)
        logging.error(prefix+": "+message)
        #raise falcon.HTTPBadRequest('Bad Request',message)
        raise falconHTTPError(falconStatusCodes.HTTP_406,'Not Acceptable',message)
    
    def _except_NotFound(self, prefix, ex):
        message = self.__get_exception_message(ex)
        logging.error(prefix+": "+message)
        #raise falcon.HTTPBadRequest('Bad Request',message)
        raise falconHTTPError(falconStatusCodes.HTTP_404,'Not Found',message)
    
    def _except_unauthorizedRequest(self,ex,request):
        username_string = ""
        if(request.get_header("X-Auth-User") is not None):
            username_string = " from user "+request.get_header("X-Auth-User")
        logging.debug("Unauthorized access attempt"+username_string+".")
        message = self.__get_exception_message(ex)
        raise falcon.HTTPUnauthorized("Unauthorized", message)
    
    def _except_requests_HTTPError(self,ex):
        logging.error(ex.response.text)
        if ex.response.status_code is not None:
            msg = ex.response.status_code+" - "
            msg += self.__get_exception_message(ex)
            raise falcon.HTTPInternalServerError('Falcon: Internal Server Error',msg)
        raise ex

    def _except_standardException(self,ex):
        message = self.__get_exception_message(ex)
        logging.exception(ex) #unique case which uses logging.exception
        raise falcon.HTTPInternalServerError('Unexpected Error - Contact the admin',message)




 
class OpenDayLightCA_REST_NFFG_Put(OpenDayLightCA_REST_Base):
    
    def on_put(self, request, response):
        try:            
            userdata = UserAuthentication().authenticateUserFromRESTRequest(request)
            
            nffg_dict = json.loads(request.stream.read().decode('utf-8'), 'utf-8')
            ValidateNF_FG().validate(nffg_dict)
            nffg = NF_FG()
            nffg.parseDict(nffg_dict)
            
            odlCA = OpenDayLightCA(userdata)
            odlCA.NFFG_Validate(nffg)
            odlCA.NFFG_Put(nffg)
    
            response.body = self._json_response(falcon.HTTP_202, message="Graph "+nffg.id+" succesfully processed.")
            response.status = falcon.HTTP_202
        
        # User auth request - raised by UserAuthentication().authenticateUserFromRESTRequest
        except wrongRequest as err:
            self._except_BadRequest("wrongRequest",err)
        
        # User auth credentials - raised by UserAuthentication().authenticateUserFromRESTRequest
        except unauthorizedRequest as err:
            self._except_unauthorizedRequest(err,request)
        
        # NFFG validation - raised by ValidateNF_FG().validate
        except NF_FGValidationError as err:
            self._except_NotAcceptable("NF_FGValidationError",err)
        
        # Custom NFFG sub-validation - raised by OpenDayLightCA().NFFG_Validate
        except NffgUselessInformations as err:
            self._except_NotAcceptable("NffgUselessInformations",err)
        
        # No Results
        except UserNotFound as err:
            self._except_NotFound("UserNotFound",err)
        except TenantNotFound as err:
            self._except_NotFound("TenantNotFound",err)
        except NoResultFound as err:
            self._except_NotFound("NoResultFound",err)
        except sessionNotFound as err:
            self._except_NotFound("sessionNotFound",err)
        
        # Other errors
        except requests.HTTPError as err:
            self._except_requests_HTTPError(err)
        except Exception as ex:
            self._except_standardException(ex)
    
    



class OpenDayLightCA_REST_NFFG_Get_Delete(OpenDayLightCA_REST_Base):
    
    def on_delete(self, request, response, nffg_id):
        try :
            
            userdata = UserAuthentication().authenticateUserFromRESTRequest(request)
            odlCA = OpenDayLightCA(userdata)
            
            odlCA.NFFG_Delete(nffg_id)
            
            response.body = self._json_response(falcon.HTTP_200, message="Graph "+nffg_id+" succesfully deleted.")
            response.status = falcon.HTTP_200

        # User auth request - raised by UserAuthentication().authenticateUserFromRESTRequest
        except wrongRequest as err:
            self._except_BadRequest("wrongRequest",err)
        
        # User auth credentials - raised by UserAuthentication().authenticateUserFromRESTRequest
        except unauthorizedRequest as err:
            self._except_unauthorizedRequest(err,request)
        
        # No Results
        except UserNotFound as err:
            self._except_NotFound("UserNotFound",err)
        except TenantNotFound:
            self._except_NotFound("TenantNotFound",err)
        except NoResultFound as err:
            self._except_NotFound("NoResultFound",err)
        except sessionNotFound as err:
            self._except_NotFound("sessionNotFound",err)
        
        # Other errors
        except requests.HTTPError as err:
            self._except_requests_HTTPError(err)
        except Exception as ex:
            self._except_standardException(ex)

    
    
    def on_get(self, request, response, nffg_id):
        try :
            userdata = UserAuthentication().authenticateUserFromRESTRequest(request)
            odlCA = OpenDayLightCA(userdata)
            
            response.body = self._json_response(falcon.HTTP_200, nffg=odlCA.NFFG_Get(nffg_id))
            response.status = falcon.HTTP_200
        
        # User auth request - raised by UserAuthentication().authenticateUserFromRESTRequest
        except wrongRequest as err:
            self._except_BadRequest("wrongRequest",err)
        
        # User auth credentials - raised by UserAuthentication().authenticateUserFromRESTRequest
        except unauthorizedRequest as err:
            self._except_unauthorizedRequest(err,request)
        
        # No Results
        except UserNotFound as err:
            self._except_NotFound("UserNotFound",err)
        except TenantNotFound as err:
            self._except_NotFound("TenantNotFound",err)
        except NoResultFound as err:
            self._except_NotFound("NoResultFound",err)
        except sessionNotFound as err:
            self._except_NotFound("sessionNotFound",err)
        
        # Other errors
        except requests.HTTPError as err:
            self._except_requests_HTTPError(err)
        except Exception as ex:
            self._except_standardException(ex)





class OpenDayLightCA_REST_NFFG_Status(OpenDayLightCA_REST_Base):
    def on_get(self, request, response, nffg_id):
        try :
            userdata = UserAuthentication().authenticateUserFromRESTRequest(request)
            odlCA = OpenDayLightCA(userdata)

            response.body = self._json_response(falcon.HTTP_200, status=odlCA.NFFG_Status(nffg_id))
            response.status = falcon.HTTP_200
        
        # User auth request - raised by UserAuthentication().authenticateUserFromRESTRequest
        except wrongRequest as err:
            self._except_BadRequest("wrongRequest",err)
        
        # User auth credentials - raised by UserAuthentication().authenticateUserFromRESTRequest
        except unauthorizedRequest as err:
            self._except_unauthorizedRequest(err,request)
        
        # No Results
        except UserNotFound as err:
            self._except_NotFound("UserNotFound",err)
        except TenantNotFound as err:
            self._except_NotFound("TenantNotFound",err)
        except NoResultFound as err:
            self._except_NotFound("NoResultFound",err)
        except sessionNotFound as err:
            self._except_NotFound("sessionNotFound",err)
        
        # Other errors
        except requests.HTTPError as err:
            self._except_requests_HTTPError(err)
        except Exception as ex:
            self._except_standardException(ex)





class OpenDayLightCA_UserAuthentication(OpenDayLightCA_REST_Base):
    def on_post(self, request, response):
        try :
            print(request.uri)
            userdata = UserAuthentication().authenticateUserFromRESTRequest(request)
            
            response.body = self._json_response(falcon.HTTP_200, userdata=userdata.getResponseJSON())
            response.status = falcon.HTTP_200
        
        # User auth request - raised by UserAuthentication().authenticateUserFromRESTRequest
        except wrongRequest as err:
            self._except_BadRequest("wrongRequest",err)
        
        # User auth credentials - raised by UserAuthentication().authenticateUserFromRESTRequest
        except unauthorizedRequest as err:
            self._except_unauthorizedRequest(err,request)
        
        # No Results
        except UserNotFound as err:
            self._except_NotFound("UserNotFound",err)
        except TenantNotFound as err:
            self._except_NotFound("TenantNotFound",err)
        except NoResultFound as err:
            self._except_NotFound("NoResultFound",err)
        except sessionNotFound as err:
            self._except_NotFound("sessionNotFound",err)
        
        # Other errors
        except requests.HTTPError as err:
            self._except_requests_HTTPError(err)
        except Exception as ex:
            self._except_standardException(ex)



