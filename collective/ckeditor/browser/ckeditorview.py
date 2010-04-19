from Acquisition import aq_inner
from zope.interface import implements, Interface
from zope.app.component.hooks import getSite
from Products.PythonScripts.standard import url_quote
from Products.Five import BrowserView
from Products.CMFCore.utils import getToolByName

from collective.ckeditor import siteMessageFactory as _

from collective.ckeditor import LOG

class ICKeditorView(Interface):
    """
    CKeditor browser view interface
    """

class CKeditorView(BrowserView):
    """
    CKeditor browser view
    """
    implements(ICKeditorView)

    def __init__(self, context, request):
        self.context = context
        self.request = request    
        self.portal = getSite()     
        self.portal_url = self.portal.absolute_url()   
        request.set('ckLoaded',True)
        
    @property
    def cke_properties(self) :
        pp = getToolByName(self.portal, 'portal_properties')
        return pp.ckeditor_properties

    def _memberUsesCKeditor(self):
        """return True if member uses CKeditor"""
        pm = getToolByName(self.portal, 'portal_membership')
        return pm.getAuthenticatedMember().getProperty('wysiwyg_editor')=='CKeditor'
    
    def contentUsesCKeditor(self, fieldname=''):
        """
        return True if content uses CKeditor
        """        
        context= aq_inner(self.context)   
        request = self.request 
        if self. _memberUsesCKeditor() :
            if not fieldname :
                return True
            if not hasattr(context, 'getField'):
                return True    
            field = context.getField(fieldname)
            if not field:
                return True
            text_format = request.get('%s_text_format' % fieldname, context.getContentType(fieldname))
            content = field.getEditAccessor(context)()
            try:
                if content.startswith('<!--'):
                    return False
            except :
                return False
            return len(content)==0 or 'html' in text_format.lower()                
        return False

    def getCK_contentsCss(self) :
        """
        return list of style sheets applied to ckeditor area
        the list is returned as a javascript string
        TODO : improve it with a control panel
        """
        context= aq_inner(self.context) 
        portal = self.portal
        portal_url = self.portal_url
        portal_css = getToolByName(portal, 'portal_css')
        css_jsList="["        
        current_skin= context.getCurrentSkinName()
        skinname = url_quote(current_skin)
        css_res= portal_css.getEvaluatedResources(context)
        for css in css_res :
           if css.getMedia() not in ('print', 'projection') and css.getRel()=='stylesheet' :
             cssPloneId = css.getId()
             cssPlone= '%s/portal_css/%s/%s' %(portal_url, skinname, cssPloneId)
             css_jsList += "'%s', " %cssPlone  
        
        
        css_jsList += "'%s/++resource/ckeditor_for_plone/ckeditor_plone_area.css']" %portal_url  
        
        return css_jsList      

    def getCK_basehref(self) :
        """
        return CK editor base href
        TODO : improve it, depending if contex isfolderish or not
        """           
        context= aq_inner(self.context) 
        return context.absolute_url()
        
        
    def getCK_finder_url(self, type) :
        """
        return browser url for a type
        """
        base_url = '%s/@@plone_ckfinder?' % self.getCK_basehref()
        if type == 'file' :
            base_url += 'typeview=file&media=file'
        elif type == 'flash' :
            flash_types = self.cke_properties.getProperty('browse_flashs_portal_types')
            base_url += 'typeview=file&media=flash'
            for type in flash_types :
                base_url += '&types:list=%s' %url_quote(type)
        elif type == 'image' :
            image_types = self.cke_properties.getProperty('browse_images_portal_types')
            base_url += 'typeview=image&media=image'
            for type in image_types :
                base_url += '&types:list=%s' %url_quote(type)
        return "'%s'" %base_url
        
    
    def getCK_params(self) :
        """
        return CK Control Panel Settings or widget Settings
        """         
        params = {}
        params['contentsCss'] = self.getCK_contentsCss()
        params['bodyId'] = "'content'"
        params['filebrowserBrowseUrl'] = self.getCK_finder_url(type='file')
        params['filebrowserImageBrowseUrl'] = self.getCK_finder_url(type='image')
        params['filebrowserFlashBrowseUrl'] = self.getCK_finder_url(type='flash')
        
        return params 

    def getCK_plone_config(self) :
        """
        return config for ckeditor
        as javascript file
        """
        request = self.request
        response = request.RESPONSE
        params_js_string = """
browser_height = jQuery(window).height();
browser_width = jQuery(window).width();

CKEDITOR.editorConfig = function( config )
{
        """
        params = self.getCK_params()
        for k, v in params.items() :
            params_js_string += """
   config.%s = %s;
            """ %(k, v)
        
        params_js_string +="""
    config.filebrowserWindowWidth = parseInt(jQuery(window).width()*80/100);
    config.filebrowserWindowHeight = parseInt(jQuery(window).height()*95/100);
};
        """
        response.setHeader('Cache-control','pre-check=0,post-check=0,must-revalidate,s-maxage=0,max-age=0,no-cache')
        response.setHeader('Content-Type', 'application/x-javascript')
        
        return params_js_string