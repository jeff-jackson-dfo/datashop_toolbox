from datashop_toolbox import OdfHeader

def remove_parameter(odfobj: OdfHeader, code: str) -> OdfHeader:
    """
    Removes a parameter from the input OdfHeader object.

    Parameters
    ----------
    odfobj: OdfHeader class object
    code: str
      A valid GF3 code (ex: code='FFFF_01')

    Returns
    -------
    odfobj: OdfHeader class object
        A modified copy of the input OdfHeader object.
    """

    # Get the parameter headers and the data records.
    data = odfobj.data.data_frame

    parameter_headers = odfobj.parameter_headers
    parameter_list = odfobj.data.parameter_list
    print_formats = odfobj.data.print_formats

    # Phase A: Look through each ODF structure's Data channels to find the code to be removed.
    for i, parameter_header in enumerate(parameter_headers):
        
        # Phase B: Remove the parameter if present.
        if parameter_header.code == code:
            
            # Step 1) Remove the associated data column.
            data = data.drop(code, axis=1)

            # Step 2) Remove the associated Parameter_Header.
            del parameter_headers[i]
            
            # Step 3) Remove associated parameter code from parameter list.
            del parameter_list[i]

            # Step 4) Remove associated print format for parameter.
            del print_formats[code]

            print("The code %s has been removed." % code)

    # Updated the associated OdfHeader object's attributes.
    odfobj.data.data_frame = data
    odfobj.data.parameter_list = parameter_list
    odfobj.data.print_formats = print_formats
    odfobj.parameter_headers = parameter_headers
    odfobj.log_odf_message(f'Parameter "{code}" was removed.', 'base')

    return odfobj
